import io
import urllib.parse
import boto3
from PIL import Image, ImageDraw, ImageFont

def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_name = urllib.parse.unquote_plus(
        event['Records'][0]['s3']['object']['key']
    )

    if file_name.startswith("output/"):
        return

    response = rekognition_detect(bucket_name, file_name)
    generate_image(bucket_name, file_name, response)


def rekognition_detect(bucket_name, file_name):
    rekognition_client = boto3.client('rekognition')

    response = rekognition_client.recognize_celebrities(
        Image={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': file_name
            }
        }
    )

    for face in response.get('CelebrityFaces', []):
        print(f"{face['Name']} - {face['MatchConfidence']:.2f}%")

    return response


def generate_image(bucket_name, file_name, response):
    s3_client = boto3.client('s3')

    # Download image from S3
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    image_bytes = s3_response['Body'].read()

    # Open it and ensure RGB for JPEG saving
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Readable sized font
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:
        # Fallback for older Pillows
        font = ImageFont.load_default()

    for face in response.get('CelebrityFaces', []):
        box = face['Face']['BoundingBox']
        name = face['Name']

        # Pixel coordinates
        left = box['Left'] * width
        top = box['Top'] * height
        right = (box['Left'] + box['Width']) * width
        bottom = (box['Top'] + box['Height']) * height
        draw.rectangle([left, top, right, bottom], outline="red", width=4)

        # Names above boxes
        text_y = max(10, top - 32)
        draw.text((left, text_y), name, fill="yellow", font=font)

    # Save image to buffer
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    # Upload image to output/
    output_key = f"output/processed-{file_name.split('/')[-1]}"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=output_key,
        Body=buffer,
        ContentType="image/jpeg"
    )
