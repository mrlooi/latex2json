def int_to_roman(num: int) -> str:
    roman_symbols = [
        ("M", 1000),
        ("CM", 900),
        ("D", 500),
        ("CD", 400),
        ("C", 100),
        ("XC", 90),
        ("L", 50),
        ("XL", 40),
        ("X", 10),
        ("IX", 9),
        ("V", 5),
        ("IV", 4),
        ("I", 1),
    ]
    result = ""
    for symbol, value in roman_symbols:
        while num >= value:
            result += symbol
            num -= value
    return result.lower()  # \romannumeral produces lowercase numerals
