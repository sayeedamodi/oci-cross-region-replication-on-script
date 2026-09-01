#!/usr/bin/env python3

import argparse
import oci
import sys
import json
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(
        description="Enable OCI Cross-Region Replication for Block and Boot Volumes"
    )

    parser.add_argument(
    "--profile",
    default="DEFAULT",
    help="OCI config profile to use"
  )  

    parser.add_argument(
        "--compartments",
        nargs="+",
        required=True,
        help="One or more compartment OCIDs"
    )

    parser.add_argument(
        "--destination-region",
        required=True,
        help="Destination OCI region, for example ap-mumbai-1"
    )

    parser.add_argument(
        "--destination-ad",
        required=True,
        help="Destination Availability Domain name"
    )

    parser.add_argument(
        "--source-region",
        default=None,
        help="Source region. Defaults to OCI config region."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )

    parser.add_argument(
        "--volume-id",
        default=None,
        help="Optional: process only this volume OCID"
    )

    return parser.parse_args()


def get_clients(config, source_region):

    identity_client = oci.identity.IdentityClient(config)

    blockstorage_client = oci.core.BlockstorageClient(config)

    bootvolume_client = oci.core.BlockstorageClient(config)

    return (
        identity_client,
        blockstorage_client,
        bootvolume_client
    )


def get_compartment_name(identity_client, compartment_id):

    try:
        compartment = identity_client.get_compartment(
            compartment_id
        ).data

        return compartment.name

    except Exception:
        return compartment_id


def get_block_volumes(blockstorage_client, compartment_id):

    volumes = []

    try:

        response = oci.pagination.list_call_get_all_results(
            blockstorage_client.list_volumes,
            compartment_id=compartment_id
        )

        volumes = response.data

    except Exception as e:

        print(
            f"[ERROR] Failed to list block volumes "
            f"in {compartment_id}: {e}"
        )

    return volumes


def get_boot_volumes(blockstorage_client, compartment_id):

    volumes = []

    try:

        response = oci.pagination.list_call_get_all_results(
            blockstorage_client.list_boot_volumes,
            compartment_id=compartment_id
        )

        volumes = response.data

    except Exception as e:

        print(
            f"[ERROR] Failed to list boot volumes "
            f"in {compartment_id}: {e}"
        )

    return volumes


def get_existing_replicas(volume):

    """
    Return existing replication configuration.

    OCI SDK model fields can vary slightly by SDK version,
    so use getattr safely.
    """

    replicas = getattr(
        volume,
        "block_volume_replicas",
        None
    )

    if replicas is None:

        replicas = getattr(
            volume,
            "boot_volume_replicas",
            None
        )

    return replicas or []


def find_destination_replica(
    volume,
    destination_region
):

    replicas = get_existing_replicas(volume)

    for replica in replicas:

        replica_region = getattr(
            replica,
            "region",
            None
        )

        if replica_region == destination_region:

            return replica

    return None


def print_volume(volume, volume_type):

    print()
    print("-" * 70)

    print(f"Type       : {volume_type}")
    print(f"Name       : {volume.display_name}")
    print(f"OCID       : {volume.id}")
    print(f"Size GB    : {getattr(volume, 'size_in_gbs', 'N/A')}")
    print(f"State      : {getattr(volume, 'lifecycle_state', 'N/A')}")

    replicas = get_existing_replicas(volume)

    print(f"Replicas   : {len(replicas)}")

    for replica in replicas:

        print(
            f"  -> Region : "
            f"{getattr(replica, 'region', 'N/A')}"
        )

        print(
            f"  -> State  : "
            f"{getattr(replica, 'lifecycle_state', 'N/A')}"
        )


def enable_block_replication(
    blockstorage_client,
    volume,
    destination_region,
    destination_ad,
    dry_run
):

    existing = find_destination_replica(
        volume,
        destination_region
    )

    if existing:

        print(
            f"[SKIP] Block Volume: {volume.display_name}"
        )

        print(
            f"       Already has replica in "
            f"{destination_region}"
        )

        return "skipped"

    print(
        f"[ENABLE] Block Volume: "
        f"{volume.display_name}"
    )

    print(
        f"         Destination Region: "
        f"{destination_region}"
    )

    print(
        f"         Destination AD: "
        f"{destination_ad}"
    )

    if dry_run:

        print(
            "         DRY RUN - no changes made"
        )

        return "dry-run"

    try:

        replica_details = [
            oci.core.models.BlockVolumeReplicaDetails(
                availability_domain=destination_ad,
                region=destination_region
            )
        ]

        details = oci.core.models.UpdateVolumeDetails(
            block_volume_replicas=replica_details
        )

        blockstorage_client.update_volume(
            volume.id,
            details
        )

        print(
            "         SUCCESS - replication enabled"
        )

        return "enabled"

    except Exception as e:

        print(
            f"         ERROR: {e}"
        )

        return "failed"


def enable_boot_replication(
    blockstorage_client,
    volume,
    destination_region,
    destination_ad,
    dry_run
):

    existing = find_destination_replica(
        volume,
        destination_region
    )

    if existing:

        print(
            f"[SKIP] Boot Volume: {volume.display_name}"
        )

        print(
            f"       Already has replica in "
            f"{destination_region}"
        )

        return "skipped"

    print(
        f"[ENABLE] Boot Volume: "
        f"{volume.display_name}"
    )

    print(
        f"         Destination Region: "
        f"{destination_region}"
    )

    print(
        f"         Destination AD: "
        f"{destination_ad}"
    )

    if dry_run:

        print(
            "         DRY RUN - no changes made"
        )

        return "dry-run"

    try:

        replica_details = [
            oci.core.models.BootVolumeReplicaDetails(
                availability_domain=destination_ad,
                region=destination_region
            )
        ]

        details = oci.core.models.UpdateBootVolumeDetails(
            boot_volume_replicas=replica_details
        )

        blockstorage_client.update_boot_volume(
            volume.id,
            details
        )

        print(
            "         SUCCESS - replication enabled"
        )

        return "enabled"

    except Exception as e:

        print(
            f"         ERROR: {e}"
        )

        return "failed"


def main():

    args = parse_args()

    print("=" * 70)
    print("OCI CROSS-REGION REPLICATION TOOL")
    print("=" * 70)

    config = oci.config.from_file(
      profile_name=args.profile
    )

    source_region = (
        args.source_region
        if args.source_region
        else config["region"]
    )

    config["region"] = source_region

    print(f"Source Region      : {source_region}")
    print(f"Destination Region : {args.destination_region}")
    print(f"Destination AD     : {args.destination_ad}")

    if args.dry_run:

        print("Mode               : DRY RUN")

    else:

        print("Mode               : APPLY")

    print(
        f"Compartments       : "
        f"{len(args.compartments)}"
    )

    print("=" * 70)

    (
        identity_client,
        blockstorage_client,
        bootvolume_client
    ) = get_clients(
        config,
        source_region
    )

    summary = {
        "block_found": 0,
        "boot_found": 0,
        "enabled": 0,
        "skipped": 0,
        "dry_run": 0,
        "failed": 0
    }

    for compartment_id in args.compartments:

        compartment_name = get_compartment_name(
            identity_client,
            compartment_id
        )

        print()
        print("#" * 70)

        print(
            f"COMPARTMENT: {compartment_name}"
        )

        print(
            f"OCID: {compartment_id}"
        )

        print("#" * 70)

        # --------------------------------------------------
        # BLOCK VOLUMES
        # --------------------------------------------------

        print()
        print("Scanning Block Volumes...")

        block_volumes = get_block_volumes(
            blockstorage_client,
            compartment_id
        )

        print(
            f"Found {len(block_volumes)} block volume(s)"
        )

        for volume in block_volumes:

            if (
                args.volume_id
                and volume.id != args.volume_id
            ):
                continue

            summary["block_found"] += 1

            print_volume(
                volume,
                "BLOCK"
            )

            result = enable_block_replication(
                blockstorage_client,
                volume,
                args.destination_region,
                args.destination_ad,
                args.dry_run
            )

            if result == "enabled":
                summary["enabled"] += 1

            elif result == "skipped":
                summary["skipped"] += 1

            elif result == "dry-run":
                summary["dry_run"] += 1

            elif result == "failed":
                summary["failed"] += 1

        # --------------------------------------------------
        # BOOT VOLUMES
        # --------------------------------------------------

        print()
        print("Scanning Boot Volumes...")

        boot_volumes = get_boot_volumes(
            blockstorage_client,
            compartment_id
        )

        print(
            f"Found {len(boot_volumes)} boot volume(s)"
        )

        for volume in boot_volumes:

            if (
                args.volume_id
                and volume.id != args.volume_id
            ):
                continue

            summary["boot_found"] += 1

            print_volume(
                volume,
                "BOOT"
            )

            result = enable_boot_replication(
                blockstorage_client,
                volume,
                args.destination_region,
                args.destination_ad,
                args.dry_run
            )

            if result == "enabled":
                summary["enabled"] += 1

            elif result == "skipped":
                summary["skipped"] += 1

            elif result == "dry-run":
                summary["dry_run"] += 1

            elif result == "failed":
                summary["failed"] += 1

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Block volumes found : "
        f"{summary['block_found']}"
    )

    print(
        f"Boot volumes found  : "
        f"{summary['boot_found']}"
    )

    print(
        f"Replication enabled : "
        f"{summary['enabled']}"
    )

    print(
        f"Already replicated  : "
        f"{summary['skipped']}"
    )

    print(
        f"Dry-run operations  : "
        f"{summary['dry_run']}"
    )

    print(
        f"Failed              : "
        f"{summary['failed']}"
    )

    print("=" * 70)


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print("\nInterrupted.")

        sys.exit(1)

    except Exception as e:

        print(
            f"\nFATAL ERROR: {e}"
        )

        sys.exit(1)
