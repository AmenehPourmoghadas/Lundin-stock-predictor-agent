#import os
#from pathlib import Path

'''

def configure_ssl() -> None:
    """
    Use the project-specific CA bundle when it exists.

    On GitHub Actions, the file will normally not exist, so the runner's
    default certificate configuration will be used.
    """
    project_root = Path(__file__).resolve().parents[2]
    ca_bundle = project_root / "certs" / "python-ca-bundle.pem"

    if not ca_bundle.exists():
        return

    bundle_path = str(ca_bundle)

    os.environ["SSL_CERT_FILE"] = bundle_path
    os.environ["REQUESTS_CA_BUNDLE"] = bundle_path
    os.environ["CURL_CA_BUNDLE"] = bundle_path
'''
from pathlib import Path


def get_ca_bundle() -> str | bool:
    """
    Return the local CA bundle if it exists.
    Otherwise return True to use the system defaults.
    """
    project_root = Path(__file__).resolve().parents[2]
    bundle = project_root / "certs" / "python-ca-bundle.pem"

    if bundle.exists():
        return str(bundle)

    return True