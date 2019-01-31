import json
from datetime import timedelta
import syslog
from .models import AcsSession, AcsDevice
from django.utils import timezone


def time_since_last_acs_session_stats(tosyslog=True):
    devicedict = {}
    for ad in AcsDevice.objects.all():
        seconds = (timezone.now() - ad.acs_sessions.latest('created_date').created_date).total_seconds()
        hours = int(seconds / 60 / 60)

        if hours in devicedict:
            devicedict[hours] += 1
        else:
            devicedict[hours] = 1

    output = {
        'mrx_stats_type': 'time_since_last_acs_session',
        'hours_since_last_session': devicedict
    }

    if tosyslog:
        syslog.openlog(facility=syslog.LOG_LOCAL3)
        syslog.syslog(json.dumps(output))
    else:
        return(output)


def acs_device_stats(tosyslog=True):
    """ Returns JSON with stats for acs devices """
    acs_devices_associated = 0
    acs_devices_unassociated = 0
    acs_devices_no_recent_session = 0
    acs_devices_with_recent_session = 0
    acs_devices_with_sessions = 0
    acs_devices_without_sessions = 0

    for ad in AcsDevice.objects.all():
        if ad.get_related_device():
            acs_devices_associated += 1
        else:
            acs_devices_unassociated += 1

        if ad.acs_sessions.exists():
            acs_devices_with_sessions += 1
            if ad.acs_sessions.latest('created_date').created_date > timezone.now() - timedelta(minutes=70):
                acs_devices_no_recent_session += 1
            else:
                acs_devices_with_recent_session += 1
        else:
            acs_devices_without_sessions += 1

    output = {
        'mrx_stats_type': 'acs_devices',
        'total_acs_devices': acs_devices_associated + acs_devices_unassociated,
        'acs_devices_associated': acs_devices_associated,
        'acs_devices_unassociated': acs_devices_unassociated,
        'acs_devices_no_recent_session': acs_devices_no_recent_session,
        'acs_devices_with_recent_session': acs_devices_with_recent_session,
        'acs_devices_with_sessions': acs_devices_with_sessions,
        'acs_devices_without_sessions': acs_devices_without_sessions,
    }

    if tosyslog:
        syslog.openlog(facility=syslog.LOG_LOCAL3)
        syslog.syslog(json.dumps(output))
    else:
        return(output)


def acs_sessions_minute(endtime=None, minutes=1, tosyslog=True):
    """ Returns JSON with stats for acs sessions from endtime and one minute in the past """
    if not endtime:
        endtime = timezone.now()
    starttime = endtime-timedelta(minutes=minutes)

    sessions = AcsSession.objects.filter(
        created_date__gt=starttime,
        created_date__lt=endtime,
    )

    total_sessions = sessions.count()

    success_sessions = 0
    success_sessions_unassociated = 0
    success_sessions_associated = 0

    failed_sessions = 0
    failed_sessions_inform_only = 0
    failed_sessions_getparametervalues = 0
    failed_sessions_other = 0

    for session in sessions:
        if session.session_result:
            success_sessions +=1
            if len(session.acs_http_conversationlist) == 4:
                # just an inform, informresponse and two empty, this is a noop session for an unknown or unassociated device
                success_sessions_unassociated +=1
            else:
                success_sessions_associated += 1
        else:
            failed_sessions += 1
            if session.acs_http_conversationlist and session.acs_http_conversationlist[0].cwmp_rpc_method == 'GetParameterValues':
                failed_sessions_getparametervalues += 1
            elif len(session.acs_http_conversationlist) == 1:
                failed_sessions_inform_only += 1
            else:
                failed_sessions_other += 1

    output = {
        'mrx_stats_type': 'acs_sessions',
        'mrxtime': endtime.isoformat(),
        'total_sessions': total_sessions,
        'success_sessions': success_sessions,
        'success_sessions_unassociated': success_sessions_unassociated,
        'success_sessions_associated': success_sessions_associated,
        'failed_sessions': failed_sessions,
        'failed_sessions_inform_only': failed_sessions_inform_only,
        'failed_sessions_getparametervalues': failed_sessions_getparametervalues
    }

    if tosyslog:
        syslog.openlog(facility=syslog.LOG_LOCAL3)
        syslog.syslog(json.dumps(output))
    else:
        return(output)

