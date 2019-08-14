from composer.aws.handshake import Handshake
from composer.aws.s3 import Bucket

def efile_bucket() -> Bucket:
    return Bucket.build("irs-form-990")
