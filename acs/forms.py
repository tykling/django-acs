from django import forms
from django.conf import settings
from defusedxml.lxml import fromstring
from django.core.exceptions import ValidationError

class AcsDeviceActionForm(forms.Form):
    action = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[(x, x) for x in settings.CWMP_CPE_VALID_RPC_METHODS]
    )

    xml = forms.CharField(
        widget=forms.Textarea,
        label="XML payload",
        help_text="Optionally (when needed) input the XML payload of the RPC call.",
        required=False
    )

    reason = forms.CharField(
        label="Reason",
        help_text="Please specify the reason why you are adding this ACS RPC call",
    )

    urgent = forms.BooleanField(
        label="Urgent?",
        help_text='Check to make this job urgent. Leave unchecked to wait until next inform.',
        required=False
    )

    def clean(self):
        cleaned_data = super(AcsDeviceActionForm, self).clean()
        errorlist = []
        if cleaned_data['xml']:
            try:
                # fromstring takes bytes, so convert the string from our form to bytes, utf-8 encoded of course
                xmlroot = fromstring(cleaned_data['xml'].encode('utf-8'))
            except Exception as E:
                errorlist.append(ValidationError('XML not valid: %s' % E, code='invalid_xml'))

        # any errors to report?
        if errorlist:
            raise ValidationError(errorlist)

        return cleaned_data


