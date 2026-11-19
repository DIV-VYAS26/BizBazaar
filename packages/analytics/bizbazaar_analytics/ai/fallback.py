from ..context import money_text


def render_summary(metrics, report_date, timezone, locale, style="standard"):
    total = money_text(metrics["collections_paise"])
    average = metrics["average_payment_paise"]
    count = metrics["successful_count"]
    if locale == "hi-IN":
        average_text = money_text(average) if average is not None else "उपलब्ध नहीं"
        text = (
            f"{report_date} ({timezone}) के दर्ज रिकॉर्ड में कुल संग्रह {total} है। "
            f"सफल भुगतान: {count}। औसत भुगतान: {average_text}। "
            "लंबित, विफल और वापस किए गए भुगतान कुल में शामिल नहीं हैं। "
            "यह केवल दर्ज गतिविधि है, पूरी दुकान की बिक्री या लाभ नहीं।"
        )
        if style == "standard" and metrics["warnings"]:
            text += " डेटा अधूरा हो सकता है; दिन की पूर्णता और सिमुलेटेड रिकॉर्ड की जाँच करें।"
        return text
    average_text = (
        money_text(average)
        if average is not None
        else "unavailable (no successful payments)"
    )
    text = (
        f"For {report_date} ({timezone}), recorded collections are {total} across {count} successful payment(s). "
        f"Average payment: {average_text}. Pending, failed and refunded records are excluded. "
        "These figures describe recorded activity, not total shop sales or profit."
    )
    if style == "standard":
        text += " " + " ".join(metrics["warnings"][1:])
    return text
