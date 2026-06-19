"""Small TwiML helpers without requiring the Twilio SDK."""

from xml.etree.ElementTree import Element, SubElement, tostring


def _xml(response: Element) -> str:
    return tostring(response, encoding="unicode", short_empty_elements=False)


def _say(parent: Element, text: str, voice: str) -> None:
    say = SubElement(parent, "Say", {"voice": voice})
    say.text = text


def gather_response(
    prompt: str,
    action_url: str,
    *,
    voice: str = "alice",
    language: str = "en-US",
) -> str:
    response = Element("Response")
    gather = SubElement(
        response,
        "Gather",
        {
            "input": "speech",
            "action": action_url,
            "method": "POST",
            "speechTimeout": "auto",
            "language": language,
        },
    )
    _say(gather, prompt, voice)

    _say(response, "I did not hear anything. Please try again.", voice)
    redirect = SubElement(response, "Redirect", {"method": "POST"})
    redirect.text = action_url
    return _xml(response)


def hangup_response(message: str, *, voice: str = "alice") -> str:
    response = Element("Response")
    _say(response, message, voice)
    SubElement(response, "Hangup")
    return _xml(response)
