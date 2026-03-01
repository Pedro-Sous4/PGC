from django.http import JsonResponse

class AjaxJsonMiddleware:
    """Convert HTML/login redirects into JSON responses for AJAX requests.

    If a request indicates it wants JSON (Accept header) or has X-Requested-With, and the
    response is HTML or a redirect to login, return a JSON response (401) instead. This
    prevents the frontend from trying to parse HTML as JSON and raising SyntaxError ('<').
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            wants_json = False
            # check typical AJAX indicators
            if (request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
                wants_json = True
            accept = request.headers.get('Accept', '') or request.META.get('HTTP_ACCEPT', '')
            if 'application/json' in accept.lower():
                wants_json = True

            if wants_json:
                # if redirect to login
                if response.status_code in (301, 302, 303, 307, 308):
                    loc = response.get('Location', '')
                    if loc and '/accounts/login' in loc:
                        return JsonResponse({'status': 'unauthenticated', 'message': 'login required'}, status=401)
                # if response is HTML when we expected JSON, convert to JSON error
                ctype = response.get('Content-Type', '')
                if isinstance(ctype, str) and 'text/html' in ctype.lower():
                    # do not clobber legitimate HTML pages for normal requests
                    # only on endpoints under /lgm/ convert to JSON to avoid breaking other flows
                    path = request.path or ''
                    if path.startswith('/lgm/'):
                        return JsonResponse({'status': 'error', 'message': 'Unexpected HTML response (likely unauthenticated) - login required or server returned HTML'}, status=401)
        except Exception:
            # fail-safe: do nothing
            pass

        return response
