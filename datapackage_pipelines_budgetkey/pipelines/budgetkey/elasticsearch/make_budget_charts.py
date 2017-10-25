from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datapackage_pipelines.wrapper import ingest, spew

parameters, dp, res_iter = ingest()


def sankey_chart(nodes, links):
    for i, node in enumerate(nodes):
        node['id'] = i
    return [{
        "type": "sankey",
        "domain": {
            "x": [0,1],
            "y": [0,1]
        },
        "orientation": "h",
        "valueformat": ".0f",
        "valuesuffix": "₪",
        "arrangement": "fixed",
        "hoverinfo": "none",
        "customdata": [node['extra'] for node in nodes],
        "node": {
            "pad": 20,
            "thickness": 60,
            "line": {
                "color": "FF5A5F",
                "width": 0.5
            },
            "label": [node['label'] for node in nodes],
            "color": [node.get('color', '#FF5A5F') for node in nodes]
        },
        "link": {
            "source": [link['source']['id'] for link in links],
            "target": [link['target']['id'] for link in links],
            "value": [link['value'] for link in links],
            "label": [link.get('label', '') for link in links],
        }
    }], {}


def budget_sankey(row, kids):
    center_node = {
        'label': row['title'],
        'extra': row['code']
    }
    links = []
    nodes = [center_node]
    if row.get('hierarchy'):
        parent_node = {
            'label': row['hierarchy'][-1][1],
            'extra': row['hierarchy'][-1][0]
        }
        nodes.append(parent_node)
        links.append({
            'source': center_node,
            'target': parent_node,
            'value': row['net_revised'],
        })
    for child in sorted(kids, key=lambda x: abs(x['amount'])):
        node = {
            'label': child['label'],
            'extra': child.get('extra')
        }
        nodes.append(node)
        amount = child['amount']
        if amount < 0:
            links.append({
                'source': center_node,
                'target': node,
                'value': -amount,
            })
        elif amount > 0:
            links.append({
                'source': node,
                'target': center_node,
                'value': amount,
            })
    return sankey_chart(nodes, links)


def category_sankey(row, prefix, translations={}):
    kids = [
        {
            'label': translations.get(k[len(prefix):], k[len(prefix):]),
            'amount': v,
        }
        for k, v in row.items()
        if k.startswith(prefix) and v is not None
    ]
    return budget_sankey(row, kids)


def query_based_charts(row):
    if False:
        yield None


def history_chart(row):
    traces = []
    history = row.get('history', [])
    if history is not None and len(history) > 0:
        years = sorted(history.keys())
        for measure, name in (
                ('net_allocated', 'תקציב מקורי'),
                ('net_revised', 'אחרי שינויים'),
                ('net_executed', 'ביצוע בפועל')
        ):
            trace = {
                'x': [int(y) for y in years] + [row['year']],
                'y': [history[year].get(measure) for year in years] + [row.get(measure)],
                'mode': 'lines+markers',
                'name': name
            }
            traces.append(trace)
        layout = {
            'xaxis': {
                'title': 'שנה',
                'type': 'category'
            },
            'yaxis': {
                'title': 'תקציב ב-₪',
                'rangemode': 'tozero',
                'separatethousands': True,
            }
        }
        return traces, layout
    return None, None


def admin_hierarchy_chart(row):
    if row.get('children'):
        # Admin Hierarchy chart
        kids = [
            {
                'label': child['title'],
                'extra': child['code'],
                'amount': child['net_revised'],
            }
            for child in row.get('children')
        ]
        return budget_sankey(row, kids)
    return None, None


def process_resource(res_):
    for row in res_:
        row['charts'] = []
        chart, layout = admin_hierarchy_chart(row)
        if chart is not None:
            row['charts'].append(
                {
                    'title': 'לאן הולך הכסף?',
                    'chart': chart,
                    'layout': layout
                }
            )
        chart, layout = history_chart(row)
        if chart is not None:
            row['charts'].append(
                {
                    'title': 'איך השתנה התקציב?',
                    'chart': chart,
                    'layout': layout
                }
            )
        chart, layout = category_sankey(row, 'total_econ_cls_', {})
        if chart is not None:
            row['charts'].append(
                {
                    'title': 'איך משתמשים בתקציב?',
                    'chart': chart,
                    'layout': layout
                }
            )
        for title, chart, layout in query_based_charts(row):
            row['charts'].append(
                {
                    'title': title,
                    'chart': chart,
                    'layout': layout
                }
            )
        yield row


def process_resources(res_iter_):
    first = next(res_iter_)
    yield process_resource(first)
    yield from res_iter_


dp['resources'][0]['schema']['fields'].append(
    {
        'name': 'charts',
        'type': 'array',
        'es:itemType': 'object',
        'es:index': False
    }
)

spew(dp, process_resources(res_iter))
