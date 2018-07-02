from datapackage_pipelines_elasticsearch.processors.dump.to_index import ESDumper
from tableschema_elasticsearch.mappers import MappingGenerator

import logging
import collections
import datetime


class BoostingMappingGenerator(MappingGenerator):

    def __init__(self):
        super(BoostingMappingGenerator, self).__init__(base={})

    @classmethod
    def _convert_type(cls, schema_type, field, prefix):
        prop = super(BoostingMappingGenerator, cls)._convert_type(schema_type, field, prefix)
        if field.get('es:keyword'):
            prop['type'] = 'keyword'
        elif schema_type == 'string':
            if field.get('es:title'):
                prop['boost'] = 100
            if field.get('es:title') or field.get('es:hebrew'):
                prop['fields'] = {
                    "hebrew": {
                    "type": "text",
                    'analyzer': 'hebrew'
                }
            }
        elif schema_type == 'integer':
            prop['index'] = True
        return prop



class DumpToElasticSearch(ESDumper):
    
    def __init__(self):
        super(DumpToElasticSearch, self).__init__(
            mapper_cls=BoostingMappingGenerator,
            index_settings={
                'index.mapping.coerce': True
            }
          )
    
    def format_datetime_rows(self, spec, rows):
        formatters = {}
        for f in spec['schema']['fields']:
            if f['type'] == 'datetime':
                if f.get('format', 'default') in ('any', 'default'):
                    formatters[f['name']] = lambda x: x.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    formatters[f['name']] = lambda x: x.strftime(f['format'])
        id = lambda x: x

        for row in rows:
            yield dict((k, formatters.get(k, id)(v)) for k, v in row.items())

    def handle_resource(self, resource, spec, parameters, datapackage):        
        return super(DumpToElasticSearch, self)\
                .handle_resource(self.format_datetime_rows(spec, resource), 
                                 spec, parameters, datapackage)


DumpToElasticSearch()()