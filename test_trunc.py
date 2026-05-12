
def _safe_dir_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)[:80]

test_val = "tensorflow_hub__faster_rcnn_inception_resnet_v2_atrous_oid_v4__hub_load_https_tfhub_dev_google_faster_rcnn_inception_resnet_v2_atrous_oid_v4_1"
print(f"Len: {len(test_val)}")
result = _safe_dir_name(test_val)
print(f"Result: {result}")
print(f"Result Len: {len(result)}")
