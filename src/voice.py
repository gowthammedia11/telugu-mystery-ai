def year_to_telugu(year):
    """
    Natural spoken Telugu year conversion.

    1930 -> పంతొమ్మిది వందల ముప్పై
    1990 -> పంతొమ్మిది వందల తొంభై
    1969 -> పంతొమ్మిది వందల అరవై తొమ్మిది
    2005 -> రెండు వేల ఐదు
    2026 -> రెండు వేల ఇరవై ఆరు
    """

    year = int(year)

    if 1900 <= year <= 1999:
        remainder = year - 1900

        if remainder == 0:
            return "పంతొమ్మిది వందలు"

        return (
            "పంతొమ్మిది వందల "
            + number_to_telugu(remainder)
        )

    if 1800 <= year <= 1899:
        remainder = year - 1800

        if remainder == 0:
            return "పద్దెనిమిది వందలు"

        return (
            "పద్దెనిమిది వందల "
            + number_to_telugu(remainder)
        )

    if 1700 <= year <= 1799:
        remainder = year - 1700

        if remainder == 0:
            return "పదిహేడు వందలు"

        return (
            "పదిహేడు వందల "
            + number_to_telugu(remainder)
        )

    if 1600 <= year <= 1699:
        remainder = year - 1600

        if remainder == 0:
            return "పదహారు వందలు"

        return (
            "పదహారు వందల "
            + number_to_telugu(remainder)
        )

    if 2000 <= year <= 2099:
        remainder = year - 2000

        if remainder == 0:
            return "రెండు వేల"

        return (
            "రెండు వేల "
            + number_to_telugu(remainder)
        )

    return number_to_telugu(year)
