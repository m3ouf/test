from rest_framework.renderers import JSONRenderer
from collections import OrderedDict


class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if not data:
            response_data = {'data': [],
                             'recordsFiltered': 0,
                             'recordsTotal': renderer_context['view'].queryset.count(),
                             "draw": int(renderer_context.get('request').GET.get('draw')) if
                             renderer_context.get('request').GET.get('draw') else 0}
            return super(CustomJSONRenderer, self).render(response_data, accepted_media_type, renderer_context)

        if isinstance(data, dict):
            if 'id' in data:  # the creation succeeded, return data
                data['message'] = 'Operation succeeded'
                return super(CustomJSONRenderer, self).render(data, accepted_media_type, renderer_context)

            if len(data) == 1 and 'detail' in data:
                data['error'] = data['detail']
                data.pop('detail')
                return super(CustomJSONRenderer, self).render(data, accepted_media_type, renderer_context)
            error_msg = ""  # creation failed, return error message
            for k, v in data.items():
                error_msg += "%s: %s\n" % (k, ", ".join(v))
            response_data = {'error': True, 'message': error_msg}
            return super(CustomJSONRenderer, self).render(response_data, accepted_media_type, renderer_context)

        # error of a multi=True serializer
        if isinstance(data, list) and all([not isinstance(item, OrderedDict) for item in data]):
            error_msg = ""
            for item in data:
                for k, v in item.items():
                    error_msg += "%s: %s\n" % (k, ", ".join(v))
            response_data = {'error': True, 'message': error_msg}
            return super(CustomJSONRenderer, self).render(response_data, accepted_media_type, renderer_context)
        values = [ordered_dict.values() for ordered_dict in data]  # listing all values
        response_data = {'data': values,
                         'recordsFiltered': renderer_context['view'].count,
                         'recordsTotal': renderer_context['view'].queryset.count()}

        if renderer_context.get('request') and renderer_context.get('request').GET:
            response_data['draw'] = int(renderer_context.get('request').GET.get('draw'))
        return super(CustomJSONRenderer, self).render(response_data, accepted_media_type, renderer_context)