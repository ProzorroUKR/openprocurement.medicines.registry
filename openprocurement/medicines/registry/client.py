import requests


class ProxyClient(object):
    def __init__(self, host, timeout=None, port=6547, version=1.0):
        self.session = requests.Session()
        self.health_url = 'http://{host}:{port}/api/{version}/health'.format(host=host, port=port, version=version)
        self.timeout = timeout

    def health(self, sandbox_mode):
        response = self.session.get(
            url=self.health_url, headers={'sandbox-mode': sandbox_mode}, timeout=self.timeout
        )

        if response.status_code == 200:
            return response

        raise requests.RequestException(
            '{} {} {}'.format(response.url, response.status_code, response.reason), response=response
        )