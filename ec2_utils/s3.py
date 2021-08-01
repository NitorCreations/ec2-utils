from threadlocal_aws.resources import s3_Bucket as bucket_r
from ec2_utils.utils import prune_array, delete_selected

def prune_s3_object_versions(bucket=None, prefix="", ten_minutely=288, hourly=168,
                             daily=30, weekly=13, monthly=6, yearly=3, dry_run=False):
    time_func = lambda version: version.last_modified
    versions = sorted(bucket_r(bucket).object_versions.filter(Prefix=prefix),
                      key=time_func, reverse=True)
    #def prune_array(prunable, time_func, group_by_func, ten_minutely=None,
    #                hourly=None, daily=None, weekly=None, monthly=None, yearly=None,
    #                dry_run=False):
    keep, delete = prune_array(versions, time_func,
                               lambda version: version.key,
                               ten_minutely=ten_minutely, hourly=hourly,
                               daily=daily, weekly=weekly, monthly=monthly,
                               yearly=yearly)
    delete_selected(versions, delete, lambda v: v.key,
                    time_func, dry_run=dry_run)
