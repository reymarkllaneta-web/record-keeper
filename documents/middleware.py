"""Small request/response hooks for the documents app."""


class AskForDeviceModel:
    """Ask browsers to send the device model with each request.

    Chrome on Android no longer puts the phone model in its user-agent string;
    it only sends it (as Sec-CH-UA-Model) to sites that ask, and only over a
    secure connection or on the computer running the system. The audit trail
    uses it to show which phone was used.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Accept-CH"] = "Sec-CH-UA-Model"
        return response
