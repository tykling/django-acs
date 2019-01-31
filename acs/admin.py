from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import *

class SearchSimpleHistoryAdmin(SimpleHistoryAdmin):
    search_fields = ['id']
    ordering = ['id']

admin.site.register(AcsSession, SearchSimpleHistoryAdmin)
admin.site.register(AcsDeviceCategory, SearchSimpleHistoryAdmin)
admin.site.register(AcsDeviceVendor, SearchSimpleHistoryAdmin)
admin.site.register(AcsDeviceModel, SearchSimpleHistoryAdmin)
admin.site.register(AcsDevice, SearchSimpleHistoryAdmin)
admin.site.register(CwmpDataModel)

@admin.register(AcsHttpRequest)
class AcsHttpRequestAdmin(SimpleHistoryAdmin):
    readonly_fields = ('acs_session', 'rpc_response_to', 'fk_body')


@admin.register(AcsHttpResponse)
class AcsHttpResponseAdmin(SimpleHistoryAdmin):
    readonly_fields = ('http_request', 'rpc_response_to', 'fk_body')

@admin.register(AcsQueueJob)
class AcsQueueJobAdmin(SimpleHistoryAdmin):
    readonly_fields = ('acs_device', 'handled_in')

