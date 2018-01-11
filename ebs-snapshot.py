import boto3 as boto3
from datetime import datetime

ec2 = boto3.client('ec2')

num_backups_to_retain = 2 # The Number Of AMI Backups You Wish To Retain For Each EC2 Instance.
instances_to_backup_tag_name = "AutoBackup" # Tag to insert on instance to get in routine. Value must be "yes" (Tag to insert on instance to get in routine. Value must be "yes" (Lowercase)
image_backup_tag_name = "ScheduledAMIBackup" # Tag Key Attached To AMIs Created By This Process. This Process Will Set Tag Value To "True".
image_backup_instance_identifier_tag_name = "ScheduledAMIInstanceId" # Tag Key Attached To AMIs Created By This Process. This Process Will Set Tag Value To The Instance ID.
delete_snaphots = True # True if you want to delete snapshots during cleanup. False if you want to only delete AMI, and leave snapshots intact.

# --------------- Helper Functions ------------------

def get_instance_name(instance):
    for tag in instance['Tags']:
        if tag['Key'] == 'Name':
            return tag['Value']
    return ''

def create_image(instance):
    instance_id = instance['InstanceId']
    ami_description = "AMI {} ({})".format(
        get_instance_name(instance),
        instance_id
    )
    ami_name = "AMI {} - {} - {}".format(
        get_instance_name(instance),
        instance_id,
        datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    )

    print("Creating Image from instance {} with ID {}...".format(
            get_instance_name(instance),
            instance_id
        )
    )

    try:

        response = ec2.create_image(
            InstanceId = instance_id,
            Description = ami_description,
            DryRun = False,
            Name = ami_name,
            NoReboot = True
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            image_id = response['ImageId']
            print("Success creating image request for Instance: {}. Image: {}".format(instance_id, image_id))

            create_image_tags(
                image_id = image_id,
                instance_name = get_instance_name(instance),
                instance_id = instance_id
            )

        # Print response to console
        print(response)

        return response
    except Exception as err:
        print(err)
        print("Failure creating image request for Instance: " + instance_id)
        raise err

def create_image_tags(image_id, instance_name, instance_id):
    resources = [image_id]
    tags = [{
        'Key': "Name",
        'Value': "AMI {} I({})".format(instance_name, instance_id)
    },
    {
        'Key': image_backup_tag_name,
        'Value': "true"
    },
    {
        'Key': image_backup_instance_identifier_tag_name,
        'Value': instance_id
    }]

    try:

        response = ec2.create_tags(
            DryRun = False,
            Resources = resources,
            Tags = tags
        )

        if response ['ResponseMetadata']['HTTPStatusCode'] == 200:
            print("Success tagging Image: " + image_id)

        # Print response to console
        print(response)

        return response
    except Exception as err:
        print(err)
        print("Failure tagging Image: " + image_id)
        raise err

def cleanup_old_backups():

    filters = [{
        'Name': 'tag:' + image_backup_tag_name,
        'Values': ['true']
    },]

    try:

        # Calls Amazon EC2 to retrieve all AMIs taggeds to backup process
        response = ec2.describe_images(DryRun=False, Filters=filters)



        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            images = response['Images']
            instances = []
            instance_dict = {}

            for image in images:
                for tag in image['Tags']:
                    if tag['Key'] == image_backup_instance_identifier_tag_name:
                        instance_id = tag['Value']
                        image_info = {
                            'ImageId': image['ImageId'],
                            'CurrentDate': image['CreationDate'],
                            'BlockDeviceMappings': image['BlockDeviceMappings']
                        }
                        if instance_dict.get(instance_id):
                            instance_dict[instance_id].append(image_info)
                        else:
                            instance_dict[instance_id] = [image_info]
                            instances.append(instance_id)

            for instance in instances:


    except Exception as err:
        print(err)
        print("Failure retrieving images for deletion.")
        raise err

# --------------- Main handler ------------------

def lambda_handler(event, context):

    filters = [{
        'Name': 'tag:' + instances_to_backup_tag_name,
        'Values': ['yes']
    },]

    try:

        # Calls Amazon EC2 to retrieve all instances tagged to backup
        response = ec2.describe_instances(DryRun=False, Filters=filters)

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:

            for reservation in response['Reservations']:
                instances_list = reservation['Instances']

                for instance in instances_list:
                    create_image(instance)

        # Print response to console
        print(response)

        return response
    except Exception as err:
        print(err)
        print("Error retrieving instances from AWS. ")
        raise err
