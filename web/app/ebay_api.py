import requests
import base64
import uuid
from .logger import setup_logger
import xml.etree.ElementTree as ET

from web.app.ebay_auth import get_ebay_token, get_ebay_user_token

logger = setup_logger(__name__)

# ebay REST API stuff
MARKETPLACE_ID = "EBAY_US"

# eBay Trading API settings
EBAY_TRADING_API_URL = "https://api.ebay.com/ws/api.dll"
SITE_ID = "0"  # 0 for US
COMPATIBILITY_LEVEL = "967"  # Use a relevant version based on documentation


def _get_trading_api_headers(call_name: str) -> dict:
    """
    Constructs common headers for eBay Trading API calls using OAuth2 token.
    """
    user_token = get_ebay_user_token()  # Get the valid user token

    headers = {
        "Content-Type": "text/xml",
        "X-EBAY-API-SITEID": SITE_ID,
        "X-EBAY-API-COMPATIBILITY-LEVEL": COMPATIBILITY_LEVEL,
        "X-EBAY-API-CALL-NAME": call_name,
        "X-EBAY-API-IAF-TOKEN": f"{user_token}",  # Use the user token
    }
    return headers


def search_ebay_by_image(image_bytes: bytes, image_type: str):
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
    }

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search_by_image"

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    params = {"filter": "itemEndDate:[..2025-05-20T00:00:00Z]"}
    payload = {"image": image_base64}  # The API expects base64-encoded string

    response = requests.post(url, headers=headers, json=payload, params=params)
    response.raise_for_status()
    return response.json()


def get_ebay_orders():
    headers = {
        "Authorization": f"Bearer {get_ebay_user_token()}",
        "Content-Type": "application/json",
    }

    url = "https://api.ebay.com/sell/fulfillment/v1/order"
    orders = []
    offset = 0
    limit = 100  # Maximum allowed limit

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            # "filter": "orderfulfillmentstatus:{FULFILLED|IN_PROGRESS}",
        }

        response = requests.get(url, headers=headers, params=params)

        try:
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            orders.extend(data.get("orders", []))
            break
            if data.get("total") is None or len(orders) >= data.get("total"):
                break

            offset += limit

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response status code: {response.status_code}")
            print(f"Response text: {response.text}")
            break  # Exit the loop if there's an error

        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the loop if there's an error

    return orders


def get_item_details(item_id):
    """
    Fetches item details (Title, Description, and ItemSpecifics) from eBay using GetItem API.
    """
    url = EBAY_TRADING_API_URL
    headers = _get_trading_api_headers("GetItem")  # Use OAuth2 headers
    body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <ItemID>{item_id}</ItemID>
      <IncludeItemCompatibilityList>true</IncludeItemCompatibilityList>
  <IncludeItemSpecifics>true</IncludeItemSpecifics>
  <DetailLevel>ReturnAll</DetailLevel>
</GetItemRequest>"""

    try:
        response = requests.post(
            url, headers=headers, data=body.encode("utf-8")
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        xml_string = response.text
        # logger.info(f"Received GetItem response from eBay API: {xml_string}")

        root = ET.fromstring(xml_string)
        ns = {"ebay": "urn:ebay:apis:eBLBaseComponents"}

        # Check for eBay API errors first
        ack = root.find(".//ebay:Ack", ns)
        if ack is not None and ack.text != "Success":
            errors = root.findall(".//ebay:Errors", ns)
            error_data = []
            for error in errors:
                short_message_elem = error.find(".//ebay:ShortMessage", ns)
                long_message_elem = error.find(".//ebay:LongMessage", ns)
                error_code_elem = error.find(".//ebay:ErrorCode", ns)
                severity_elem = error.find(".//ebay:SeverityCode", ns)
                classification_elem = error.find(
                    ".//ebay:ErrorClassification", ns
                )

                error_info = {
                    "short_message": (
                        short_message_elem.text
                        if short_message_elem is not None
                        else "Unknown error"
                    ),
                    "long_message": (
                        long_message_elem.text
                        if long_message_elem is not None
                        else "No details available"
                    ),
                    "error_code": (
                        error_code_elem.text
                        if error_code_elem is not None
                        else "N/A"
                    ),
                    "severity": (
                        severity_elem.text
                        if severity_elem is not None
                        else "Unknown"
                    ),
                    "classification": (
                        classification_elem.text
                        if classification_elem is not None
                        else "Unknown"
                    ),
                }
                error_data.append(error_info)

            return (
                None,
                None,
                None,
                {"type": "structured", "errors": error_data},
            )

        # If success, extract title, description, and item specifics
        item_element = root.find(".//ebay:Item", ns)
        if item_element is not None:
            title_element = item_element.find(".//ebay:Title", ns)
            description_element = item_element.find(".//ebay:Description", ns)
            item_specifics_element = item_element.find(
                ".//ebay:ItemSpecifics", ns
            )

            title = title_element.text if title_element is not None else "N/A"
            description = (
                description_element.text
                if description_element is not None
                else "N/A"
            )

            # Convert ItemSpecifics element to XML string if it exists
            item_specifics_xml = ""
            if item_specifics_element is not None:
                item_specifics_xml = ET.tostring(
                    item_specifics_element, encoding="unicode"
                )
                # Remove the namespace declaration to clean it up for insertion
                item_specifics_xml = item_specifics_xml.replace(
                    ' xmlns="urn:ebay:apis:eBLBaseComponents"', ""
                )
                # Add proper indentation for insertion into AddItemRequest
                item_specifics_xml = "    " + item_specifics_xml.replace(
                    "\n", "\n    "
                )

            return (
                title,
                description,
                item_specifics_xml,
                None,
            )  # Return title, description, item_specifics, and no error
        else:
            return None, None, None, "Item element not found in response"

    except requests.exceptions.RequestException as e:
        error_data = [
            {
                "short_message": "Network Request Failed",
                "long_message": f"Failed to communicate with eBay API: {str(e)}",
                "error_code": "NETWORK_ERROR",
                "severity": "Error",
                "classification": "RequestError",
            }
        ]
        return None, None, None, {"type": "structured", "errors": error_data}
    except ET.ParseError as e:
        error_data = [
            {
                "short_message": "XML Parsing Error",
                "long_message": f"Failed to parse eBay API response: {str(e)}",
                "error_code": "XML_PARSE_ERROR",
                "severity": "Error",
                "classification": "ResponseError",
            }
        ]
        return None, None, None, {"type": "structured", "errors": error_data}
    except Exception as e:
        error_data = [
            {
                "short_message": "Unexpected Error",
                "long_message": f"An unexpected error occurred while processing the request: {str(e)}",
                "error_code": "UNKNOWN_ERROR",
                "severity": "Error",
                "classification": "SystemError",
            }
        ]
        return None, None, None, {"type": "structured", "errors": error_data}


def upload_site_hosted_pictures(image_file, filename):
    """
    Uploads an image to eBay using UploadSiteHostedPictures API.
    Returns the FullURL on success or error data on failure.
    """
    url = EBAY_TRADING_API_URL
    headers = _get_trading_api_headers("UploadSiteHostedPictures")

    # Remove Content-Type from headers as we'll set it for multipart
    headers.pop("Content-Type", None)

    # Create the XML payload
    xml_payload = """<?xml version="1.0" encoding="utf-8"?>
<UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <PictureSet>Standard</PictureSet>
    <ExtensionInDays>20</ExtensionInDays>
</UploadSiteHostedPicturesRequest>"""

    # Create multipart form data
    boundary = f"----FormBoundary{uuid.uuid4().hex}"
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    # Build multipart body
    body_parts = []

    # Add XML payload
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(
        'Content-Disposition: form-data; name="XML Payload"\r\n\r\n'
    )
    body_parts.append(xml_payload)
    body_parts.append("\r\n")

    # Add image file
    body_parts.append(f"--{boundary}\r\n")
    body_parts.append(
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
    )

    # Determine content type based on file extension
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
    else:
        content_type = "image/jpeg"  # Default

    body_parts.append(f"Content-Type: {content_type}\r\n\r\n")

    # Convert string parts to bytes
    body_bytes = "".join(body_parts).encode("utf-8")

    # Add binary image data
    body_bytes += image_file
    body_bytes += f"\r\n--{boundary}--\r\n".encode("utf-8")
    logger.info(f"Image XML headers {headers}")
    # logger.info(f"Image XML {body_bytes}")
    try:
        logger.info(f"Uploading image {filename} to eBay...")
        response = requests.post(url, headers=headers, data=body_bytes)
        response.raise_for_status()

        xml_string = response.text
        logger.info(f"Received UploadSiteHostedPictures response: {xml_string}")

        root = ET.fromstring(xml_string)
        ns = {"ebay": "urn:ebay:apis:eBLBaseComponents"}

        # Check for eBay API errors
        ack = root.find(".//ebay:Ack", ns)
        if ack is not None and ack.text != "Success":
            errors = root.findall(".//ebay:Errors", ns)
            error_data = []
            for error in errors:
                short_message_elem = error.find(".//ebay:ShortMessage", ns)
                long_message_elem = error.find(".//ebay:LongMessage", ns)
                error_code_elem = error.find(".//ebay:ErrorCode", ns)
                severity_elem = error.find(".//ebay:SeverityCode", ns)
                classification_elem = error.find(
                    ".//ebay:ErrorClassification", ns
                )

                error_info = {
                    "short_message": (
                        short_message_elem.text
                        if short_message_elem is not None
                        else "Unknown error"
                    ),
                    "long_message": (
                        long_message_elem.text
                        if long_message_elem is not None
                        else "No details available"
                    ),
                    "error_code": (
                        error_code_elem.text
                        if error_code_elem is not None
                        else "N/A"
                    ),
                    "severity": (
                        severity_elem.text
                        if severity_elem is not None
                        else "Unknown"
                    ),
                    "classification": (
                        classification_elem.text
                        if classification_elem is not None
                        else "Unknown"
                    ),
                }
                error_data.append(error_info)

            return None, {"type": "structured", "errors": error_data}

        # Extract the FullURL from successful response
        picture_details = root.find(".//ebay:SiteHostedPictureDetails", ns)
        if picture_details is not None:
            full_url_elem = picture_details.find(".//ebay:FullURL", ns)
            if full_url_elem is not None:
                return full_url_elem.text, None

        return None, {
            "type": "structured",
            "errors": [
                {
                    "short_message": "Upload failed",
                    "long_message": "No picture URL returned",
                    "error_code": "NO_URL",
                    "severity": "Error",
                    "classification": "ResponseError",
                }
            ],
        }

    except requests.exceptions.RequestException as e:
        error_data = [
            {
                "short_message": "Network Request Failed",
                "long_message": f"Failed to upload image to eBay: {str(e)}",
                "error_code": "NETWORK_ERROR",
                "severity": "Error",
                "classification": "RequestError",
            }
        ]
        return None, {"type": "structured", "errors": error_data}
    except ET.ParseError as e:
        error_data = [
            {
                "short_message": "XML Parsing Error",
                "long_message": f"Failed to parse eBay upload response: {str(e)}",
                "error_code": "XML_PARSE_ERROR",
                "severity": "Error",
                "classification": "ResponseError",
            }
        ]
        return None, {"type": "structured", "errors": error_data}
    except Exception as e:
        error_data = [
            {
                "short_message": "Unexpected Error",
                "long_message": f"An unexpected error occurred during image upload: {str(e)}",
                "error_code": "UNKNOWN_ERROR",
                "severity": "Error",
                "classification": "SystemError",
            }
        ]
        return None, {"type": "structured", "errors": error_data}


def add_new_item(
    title: str,
    description: str,
    item_specifics_xml: str = "",
    picture_urls: list = None,
):
    """
    Creates a new eBay listing draft using AddItem API with provided title, description, and images.
    """
    url = EBAY_TRADING_API_URL
    headers = _get_trading_api_headers("AddItem")  # Use OAuth2 headers

    # Build picture details XML if picture URLs are provided
    picture_details_xml = ""
    if picture_urls is None:
        picture_urls = []
    if picture_urls:
        picture_urls_xml = ""
        for picture_url in picture_urls:
            picture_urls_xml += (
                f"      <PictureURL>{picture_url}</PictureURL>\n"
            )

        picture_details_xml = f"""    <PictureDetails>
{picture_urls_xml}    </PictureDetails>"""

    body = f"""<?xml version="1.0" encoding="utf-8"?>
<AddItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <ErrorLanguage>en_US</ErrorLanguage>
  <WarningLevel>High</WarningLevel>
  <Item>
    <Title>{title}</Title>
    <Description><![CDATA[ {description} ]]></Description>
    <StartPrice currencyID="USD">2.00</StartPrice>
    <CategoryMappingAllowed>true</CategoryMappingAllowed>
    <PrimaryCategory>
        <CategoryID>261328</CategoryID>
    </PrimaryCategory>
    <Quantity>1</Quantity>
    <ListingType>FixedPriceItem</ListingType>
    <ListingDuration>GTC</ListingDuration>
    <Location>Atlanta, GA</Location>
    <PostalCode>30318</PostalCode>
    <Country>US</Country>
    <Currency>USD</Currency>
    <ShippingDetails>
      <ShippingServiceOptions>
        <ShippingService>US_eBayStandardEnvelope</ShippingService>
        <ShippingServiceCost currencyID="USD">1.25</ShippingServiceCost>
        <ShippingServicePriority>1</ShippingServicePriority>
      </ShippingServiceOptions>
      <ShippingType>Flat</ShippingType>
    </ShippingDetails>
    <ShippingPackageDetails>
        <PackageDepth>1</PackageDepth>
        <PackageLength>11</PackageLength>
        <PackageWidth>6</PackageWidth>
        <WeightMajor>0</WeightMajor>
        <WeightMinor>1</WeightMinor>
    </ShippingPackageDetails>
    <ReturnPolicy>
      <ReturnsAcceptedOption>ReturnsNotAccepted</ReturnsAcceptedOption>
      <ReturnsAccepted>No returns accepted</ReturnsAccepted>
      <InternationalReturnsAcceptedOption>ReturnsNotAccepted</InternationalReturnsAcceptedOption>
    </ReturnPolicy>
    <DispatchTimeMax>2</DispatchTimeMax>
    <ConditionID>4000</ConditionID>
    <ConditionDescriptors>
      <ConditionDescriptor>
        <Name>40001</Name>
        <Value>400010</Value>
      </ConditionDescriptor>
    </ConditionDescriptors>
    {item_specifics_xml}
    {picture_details_xml}
  </Item>
</AddItemRequest>"""

    try:
        logger.info(f"Sending AddItemRequest request to eBay API...\n{body}")
        response = requests.post(
            url, headers=headers, data=body.encode("utf-8")
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        xml_string = response.text
        logger.info(
            f"Received AddItemRequest response from eBay API: \n{xml_string}"
        )
        root = ET.fromstring(xml_string)
        ns = {"ebay": "urn:ebay:apis:eBLBaseComponents"}

        # Check for eBay API errors and warnings
        ack = root.find(".//ebay:Ack", ns)
        errors = root.findall(".//ebay:Errors", ns)
        error_data = []
        warning_data = []

        for error in errors:
            short_message_elem = error.find(".//ebay:ShortMessage", ns)
            long_message_elem = error.find(".//ebay:LongMessage", ns)
            error_code_elem = error.find(".//ebay:ErrorCode", ns)
            severity_elem = error.find(".//ebay:SeverityCode", ns)
            classification_elem = error.find(".//ebay:ErrorClassification", ns)

            error_info = {
                "short_message": (
                    short_message_elem.text
                    if short_message_elem is not None
                    else "Unknown error"
                ),
                "long_message": (
                    long_message_elem.text
                    if long_message_elem is not None
                    else "No details available"
                ),
                "error_code": (
                    error_code_elem.text
                    if error_code_elem is not None
                    else "N/A"
                ),
                "severity": (
                    severity_elem.text
                    if severity_elem is not None
                    else "Unknown"
                ),
                "classification": (
                    classification_elem.text
                    if classification_elem is not None
                    else "Unknown"
                ),
            }

            # Separate errors from warnings
            if error_info["severity"] == "Warning":
                warning_data.append(error_info)
            else:
                error_data.append(error_info)

        # If there are actual errors (not just warnings), return error
        if ack is not None and ack.text == "Failure":
            return None, None, {"type": "structured", "errors": error_data}

        # Extract new item ID and fees (success or warning case)
        item_id_element = root.find(".//ebay:ItemID", ns)
        fees_element = root.find(".//ebay:Fees", ns)

        new_item_id = (
            item_id_element.text if item_id_element is not None else "N/A"
        )
        fees_data = []
        if fees_element is not None:
            for fee in fees_element.findall(".//ebay:Fee", ns):
                name_element = fee.find(".//ebay:Name", ns)
                fee_value_element = fee.find(
                    ".//ebay:Fee", ns
                )  # The fee value element is also named "Fee"
                if name_element is not None and fee_value_element is not None:
                    fees_data.append(
                        {
                            "name": name_element.text,
                            "fee": fee_value_element.text,
                        }
                    )

        # Return success with warnings if any
        warnings = (
            {"type": "structured", "errors": warning_data}
            if warning_data
            else None
        )
        return new_item_id, fees_data, warnings

    except requests.exceptions.RequestException as e:
        error_data = [
            {
                "short_message": "Network Request Failed",
                "long_message": f"Failed to communicate with eBay API: {str(e)}",
                "error_code": "NETWORK_ERROR",
                "severity": "Error",
                "classification": "RequestError",
            }
        ]
        return None, None, {"type": "structured", "errors": error_data}
    except ET.ParseError as e:
        error_data = [
            {
                "short_message": "XML Parsing Error",
                "long_message": f"Failed to parse eBay API response: {str(e)}",
                "error_code": "XML_PARSE_ERROR",
                "severity": "Error",
                "classification": "ResponseError",
            }
        ]
        return None, None, {"type": "structured", "errors": error_data}
    except Exception as e:
        error_data = [
            {
                "short_message": "Unexpected Error",
                "long_message": f"An unexpected error occurred while processing the request: {str(e)}",
                "error_code": "UNKNOWN_ERROR",
                "severity": "Error",
                "classification": "SystemError",
            }
        ]
        return None, None, {"type": "structured", "errors": error_data}
