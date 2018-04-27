"""
see: https://blogs.msdn.microsoft.com/translation/
see: https://blogs.msdn.microsoft.com/uk_faculty_connection/2017/08/21/microsoft-cognitive-services-translation-api-with-python-c/
see: https://cognitive.uservoice.com/knowledgebase/articles/1141621-api-translator-text-speech-why-are-there-two
see: https://cognitive.uservoice.com/knowledgebase/articles/1815385-api-translator-text-speech-using-the-api-key
"""

import requests
import xml.etree.ElementTree as ET

translateUrl = 'https://api.microsofttranslator.com/v2/http.svc/Translate'

def translate(text, target_code, subscription, source_code='it'):
    """ Using Python for Text Translation with Microsoft Cognitive Services """

    # Specify the subscription Key
    subscriptionKey = subscription.secret_1

    """
    # Specify URLs for Cognitive Services
    cognitiveServiceUrl = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'
    # Request Access Token
    requestHeader = {'Ocp-Apim-Subscription-Key': subscriptionKey}
    responseResult = requests.post(cognitiveServiceUrl, headers=requestHeader)
    token = responseResult.text
    params = {'appid': 'Bearer '+token, 'text': text, 'from': source_code, 'to': target_code}
    requestHeader = {'Accept': 'application/xml'}
    """

    # Define Parameters
    params = {'text': text, 'from': source_code, 'to': target_code}
    requestHeader = {'Ocp-Apim-Subscription-Key': subscriptionKey, 'Accept': 'application/xml'}

    # Invoke Cognitive Services to perform translation
    response = requests.get(translateUrl, params=params, headers=requestHeader)
    if response.status_code == requests.codes.ok:
        xml_text = response.text
        xml_element = ET.fromstring(xml_text)
        translation = xml_element.text.strip()
        return translation
    else:
        return ''
