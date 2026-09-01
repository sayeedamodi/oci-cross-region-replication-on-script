#!/usr/bin/env python3

import argparse
import sys
import oci


def parse_args():
    parser = argparse.ArgumentParser(
        description="OCI Cross-Region Replication for Block and Boot Volumes"
    )

    parser.add_argument(
        "--compartments-file",
        required=True,
        help="TXT file containing compartment OCIDs, one per line"
    )

    parser.add_argument(
        "--destination-region",
        required=True,
        help="Destination OCI region, e.g. ap-mumbai-1"
    )

    parser.add_argument(
        "--destination-ad",
        required=True,
        help="Destination Availability Domain"
    )

    parser.add_argument(
        "--source-region",
        help="Source OCI region. Defaults to region in OCI profile."
    )

    parser.add_argument(
        "--profile",
        default="DEFAULT",
        help="OCI config profile. Default: DEFAULT"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )

    parser.add_argument(
        "--volume-id",
        help="Optional: process only this volume OCID"
    )

    return parser.parse_args()


def load_compartments(filename):
    compartments = []

    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()

                # Ignore blank lines
                if not line:
                    continue

                # Ignore comments
                if line.startswith("#"):
                    continue

                compartments.append(line)

    except FileNotFoundError:
        print(f"[ERROR] Compartment file not found: {filename}")
        sys.exit(1)

    if not compartments:
        print("[ERROR] No compartment OCIDs found in file.")
        sys.exit(1)

    return compartments


def get_compartment_name(identity_client, compartment_id):
    try:
        response = identity_client.get_compartment(
            compartment_id
        )

        return response.data.name

    except Exception:
        return compartment_id


def get_block_volumes(blockstorage_client, compartment_id):
    try:
        response = oci.pagination.list_call_get_all_results(
            blockstorage_client.list_volumes,
            compartment_id=compartment_id
        )

        return response.data

    except Exception as e:
        print(
            f"[ERROR] Failed to list block volumes "
            f"in {compartment_id}: {e}"
        )

        return []


def get_boot_volumes(blockstorage_client, compartment_id):
    try:
        response = oci.pagination.list_call_get_all_results(
            blockstorage_client.list_boot_volumes,
            compartment_id=compartment_id
        )

        return response.data

    except Exception as e:
        print(
            f"[ERROR] Failed to list boot volumes "
            f"in {compartment_id}: {e}"
        )

        return []


def get_block_replicas(volume):
    return getattr(
        volume,
        "block_volume_replicas",
        []
    ) or []


def get_boot_replicas(volume):
    return getattr(
        volume,
        "boot_volume_replicas",
        []
    ) or []


def replica_matches_destination(replica, destination_region, destination_ad):
    replica_region = getattr(
        replica,
        "region",
        None
    )

    replica_ad = getattr(
        replica,
        "availability_domain",
        None
    )

    # Some OCI responses identify the destination through
    # the availability domain. Check both where available.
    if replica_region == destination_region:
        return True

    if replica_ad == destination_ad:
        return True

    return False


def print_volume_info(volume, volume_type, replicas):
    print()
    print("-" * 70)

    print(f"Type       : {volume_type}")
    print(f"Name       : {volume.display_name}")
    print(f"OCID       : {volume.id}")
    print(
        f"Size GB    : "
        f"{getattr(volume, 'size_in_gbs', 'N/A')}"
    )
    print(
        f"State      : "
        f"{getattr(volume, 'lifecycle_state', 'N/A')}"
    )
    print(f"Replicas   : {len(replicas)}")

    for replica in replicas:
        print(
            f"  Replica AD     : "
            f"{getattr(replica, 'availability_domain', 'N/A')}"
        )

        print(
            f"  Replica Region : "
            f"{getattr(replica, 'region', 'N/A')}"
        )

        print(
            f"  Replica State  : "
            f"{getattr(replica, 'lifecycle_state', 'N/A')}"
        )


def enable_block_replication(
    blockstorage_client,
    volume,
    destination_region,
    destination_ad,
    dry_run
):

    replicas = get_block_replicas(volume)

    for replica in replicas:

        if replica_matches_destination(
            replica,
            destination_region,
            destination_ad
        ):

            print(
                f"[SKIP] Block Volume: "
                f"{volume.display_name}"
            )

            print(
                f"       Replica already exists "
                f"in requested destination."
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
                xrr_kms_key_id=None
            )
        ]

        update_details = oci.core.models.UpdateVolumeDetails(
            block_volume_replicas=replica_details
        )

        blockstorage_client.update_volume(
            volume.id,
            update_details
        )

        print(
            "         SUCCESS - replication request submitted"
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

    replicas = get_boot_replicas(volume)

    for replica in replicas:

        if replica_matches_destination(
            replica,
            destination_region,
            destination_ad
        ):

            print(
                f"[SKIP] Boot Volume: "
                f"{volume.display_name}"
            )

            print(
                f"       Replica already exists "
                f"in requested destination."
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
                xrr_kms_key_id=None
            )
        ]

        update_details = oci.core.models.UpdateBootVolumeDetails(
            boot_volume_replicas=replica_details
        )

        blockstorage_client.update_boot_volume(
            volume.id,
            update_details
        )

        print(
            "         SUCCESS - replication request submitted"
        )

        return "enabled"

    except Exception as e:

        print(
            f"         ERROR: {e}"
        )

        return "failed"


def main():

    args = parse_args()

    print()
    print("=" * 70)
    print("OCI CROSS-REGION REPLICATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load OCI profile
    # ---------------------------------------------------------

    try:

        config = oci.config.from_file(
            profile_name=args.profile
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to load OCI profile "
            f"'{args.profile}': {e}"
        )

        sys.exit(1)

    # ---------------------------------------------------------
    # Source region
    # ---------------------------------------------------------

    source_region = (
        args.source_region
        if args.source_region
        else config["region"]
    )

    config["region"] = source_region

    # ---------------------------------------------------------
    # Load compartments
    # ---------------------------------------------------------

    compartments = load_compartments(
        args.compartments_file
    )

    print(f"Profile             : {args.profile}")
    print(f"Source Region       : {source_region}")
    print(
        f"Destination Region  : "
        f"{args.destination_region}"
    )
    print(
        f"Destination AD      : "
        f"{args.destination_ad}"
    )
    print(
        f"Compartments File   : "
        f"{args.compartments_file}"
    )
    print(
        f"Compartments        : "
        f"{len(compartments)}"
    )

    if args.dry_run:
        print("Mode                : DRY RUN")
    else:
        print("Mode                : APPLY")

    print("=" * 70)

    # ---------------------------------------------------------
    # OCI clients
    # ---------------------------------------------------------

    identity_client = oci.identity.IdentityClient(
        config
    )

    blockstorage_client = oci.core.BlockstorageClient(
        config
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    summary = {
        "compartments": 0,
        "block_found": 0,
        "boot_found": 0,
        "enabled": 0,
        "skipped": 0,
        "dry_run": 0,
        "failed": 0
    }

    # ---------------------------------------------------------
    # Process compartments
    # ---------------------------------------------------------

    for compartment_id in compartments:

        summary["compartments"] += 1

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
            f"OCID       : {compartment_id}"
        )
        print("#" * 70)

        # =====================================================
        # BLOCK VOLUMES
        # =====================================================

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

            replicas = get_block_replicas(
                volume
            )

            print_volume_info(
                volume,
                "BLOCK",
                replicas
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

        # =====================================================
        # BOOT VOLUMES
        # =====================================================

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

            replicas = get_boot_replicas(
                volume
            )

            print_volume_info(
                volume,
                "BOOT",
                replicas
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

    # ---------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Compartments scanned : "
        f"{summary['compartments']}"
    )

    print(
        f"Block volumes found  : "
        f"{summary['block_found']}"
    )

    print(
        f"Boot volumes found   : "
        f"{summary['boot_found']}"
    )

    print(
        f"Replication enabled  : "
        f"{summary['enabled']}"
    )

    print(
        f"Already replicated   : "
        f"{summary['skipped']}"
    )

    print(
        f"Dry-run operations   : "
        f"{summary['dry_run']}"
    )

    print(
        f"Failed               : "
        f"{summary['failed']}"
    )

    print("=" * 70)


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print()
        print("Interrupted by user.")
        sys.exit(1)

    except Exception as e:

        print()
        print(f"FATAL ERROR: {e}")
        sys.exit(1)
