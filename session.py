# -*- coding: utf-8 -*-"""

def get_clipboard(request, key=None):
    clipboard = request.session.get("clipboard", None)
    if not clipboard:
        clipboard = {}
    if key:
        return clipboard.get(key, None)
    else:
        return clipboard

def set_clipboard(request, key=None, value=None):
    clipboard = get_clipboard(request)
    if key:
        if value:
            clipboard[key] = value
        elif clipboard.get(key, None):
            del clipboard[key]
    request.session["clipboard"] = clipboard

def get_language(request):
    return request.session.get("language", '')

def set_language(request, value):
    request.session["language"] = value

def get_site(request):
    return request.session.get("site", '')

def set_site(request, value):
    request.session["site"] = value

def get_userrole(request):
    return request.session.get("userrole", '')

def set_userrole(request, value):
    request.session["userrole"] = value
