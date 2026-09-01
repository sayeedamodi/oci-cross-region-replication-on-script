# OCI Cross-Region Replication

Python script to scan OCI compartments and enable Cross-Region Replication for **Block Volumes** and **Boot Volumes**.

## Requirements

Install OCI Python SDK:

```bash
pip install oci
```

Configure OCI credentials:

```bash
oci setup config
```

## 1. Add Compartment OCIDs

Create `compartments.txt`:

```text
ocid1.compartment.oc1..aaaa
ocid1.compartment.oc1..bbbb
ocid1.compartment.oc1..cccc
```

Add one compartment OCID per line.

## 2. Dry Run

Test without making changes:

```bash
python oci-crros.py \
  --compartments-file compartments.txt \
  --source-region ap-hyderabad-1 \
  --destination-region ap-mumbai-1 \
  --destination-ad <DESTINATION_AD> \
  --dry-run
```

## 3. Enable Replication

After verifying the dry run:

```bash
python oci-crros.py \
  --compartments-file compartments.txt \
  --source-region ap-hyderabad-1 \
  --destination-region ap-mumbai-1 \
  --destination-ad <DESTINATION_AD>
```

## 4. Multiple OCI Profiles

Use a specific profile:

```bash
python oci-crros.py \
  --profile PROD \
  --compartments-file compartments.txt \
  --source-region ap-hyderabad-1 \
  --destination-region ap-mumbai-1 \
  --destination-ad <DESTINATION_AD> \
  --dry-run
```

## Important

The destination region must be subscribed to your OCI tenancy before enabling Cross-Region Replication.
