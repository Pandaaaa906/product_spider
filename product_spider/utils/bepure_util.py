def md5(sMessage):
    """
    接口请求需要生成签名
    :param sMessage: product_id(170000002) + "GOODS_INFO_CHECK_KEY" + 当前时间戳(1731032611281)
    :return:
    """

    def rotate_left(lValue, iShiftBits):
        return (lValue << iShiftBits) | (lValue >> (32 - iShiftBits))

    def add_unsigned(lX, lY):
        lX4 = lX & 0x40000000
        lY4 = lY & 0x40000000
        lX8 = lX & 0x80000000
        lY8 = lY & 0x80000000
        lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF)
        if lX4 & lY4:
            return lResult ^ 0x80000000 ^ lX8 ^ lY8
        if lX4 | lY4:
            if lResult & 0x40000000:
                return lResult ^ 0xC0000000 ^ lX8 ^ lY8
            else:
                return lResult ^ 0x40000000 ^ lX8 ^ lY8
        else:
            return lResult ^ lX8 ^ lY8

    def F(x, y, z):
        return (x & y) | (~x & z)

    def G(x, y, z):
        return (x & z) | (y & ~z)

    def H(x, y, z):
        return x ^ y ^ z

    def I(x, y, z):
        return y ^ (x | ~z)

    def FF(a, b, c, d, x, s, ac):
        a = add_unsigned(a, add_unsigned(add_unsigned(F(b, c, d), x), ac))
        return add_unsigned(rotate_left(a, s), b)

    def GG(a, b, c, d, x, s, ac):
        a = add_unsigned(a, add_unsigned(add_unsigned(G(b, c, d), x), ac))
        return add_unsigned(rotate_left(a, s), b)

    def HH(a, b, c, d, x, s, ac):
        a = add_unsigned(a, add_unsigned(add_unsigned(H(b, c, d), x), ac))
        return add_unsigned(rotate_left(a, s), b)

    def II(a, b, c, d, x, s, ac):
        a = add_unsigned(a, add_unsigned(add_unsigned(I(b, c, d), x), ac))
        return add_unsigned(rotate_left(a, s), b)

    def convert_to_word_array(sMessage):
        lMessageLength = len(sMessage)
        lNumberOfWords = (((lMessageLength + 8) // 64) + 1) * 16
        lWordArray = [0] * lNumberOfWords
        for i in range(lMessageLength):
            lWordArray[i >> 2] |= ord(sMessage[i]) << ((i % 4) * 8)
        lWordArray[lMessageLength >> 2] |= 0x80 << ((lMessageLength % 4) * 8)
        lWordArray[-2] = lMessageLength * 8
        return lWordArray

    def word_to_hex(lValue):
        hex_value = ""
        for i in range(4):
            hex_value += '{:02x}'.format((lValue >> (i * 8)) & 0xFF)
        return hex_value

    x = convert_to_word_array(sMessage)
    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476
    S11, S12, S13, S14 = 7, 12, 17, 22
    S21, S22, S23, S24 = 5, 9, 14, 20
    S31, S32, S33, S34 = 4, 11, 16, 23
    S41, S42, S43, S44 = 6, 10, 15, 21
    for k in range(0, len(x), 16):
        AA, BB, CC, DD = a, b, c, d

        a = FF(a, b, c, d, x[k + 0], S11, 0xD76AA478)
        d = FF(d, a, b, c, x[k + 1], S12, 0xE8C7B756)
        c = FF(c, d, a, b, x[k + 2], S13, 0x242070DB)
        b = FF(b, c, d, a, x[k + 3], S14, 0xC1BDCEEE)
        a = FF(a, b, c, d, x[k + 4], S11, 0xF57C0FAF)
        d = FF(d, a, b, c, x[k + 5], S12, 0x4787C62A)
        c = FF(c, d, a, b, x[k + 6], S13, 0xA8304613)
        b = FF(b, c, d, a, x[k + 7], S14, 0xFD469501)
        a = FF(a, b, c, d, x[k + 8], S11, 0x698098D8)
        d = FF(d, a, b, c, x[k + 9], S12, 0x8B44F7AF)
        c = FF(c, d, a, b, x[k + 10], S13, 0xFFFF5BB1)
        b = FF(b, c, d, a, x[k + 11], S14, 0x895CD7BE)
        a = FF(a, b, c, d, x[k + 12], S11, 0x6B901122)
        d = FF(d, a, b, c, x[k + 13], S12, 0xFD987193)
        c = FF(c, d, a, b, x[k + 14], S13, 0xA679438E)
        b = FF(b, c, d, a, x[k + 15], S14, 0x49B40821)

        a = GG(a, b, c, d, x[k + 1], S21, 0xF61E2562)
        d = GG(d, a, b, c, x[k + 6], S22, 0xC040B340)
        c = GG(c, d, a, b, x[k + 11], S23, 0x265E5A51)
        b = GG(b, c, d, a, x[k + 0], S24, 0xE9B6C7AA)
        a = GG(a, b, c, d, x[k + 5], S21, 0xD62F105D)
        d = GG(d, a, b, c, x[k + 10], S22, 0x2441453)
        c = GG(c, d, a, b, x[k + 15], S23, 0xD8A1E681)
        b = GG(b, c, d, a, x[k + 4], S24, 0xE7D3FBC8)
        a = GG(a, b, c, d, x[k + 9], S21, 0x21E1CDE6)
        d = GG(d, a, b, c, x[k + 14], S22, 0xC33707D6)
        c = GG(c, d, a, b, x[k + 3], S23, 0xF4D50D87)
        b = GG(b, c, d, a, x[k + 8], S24, 0x455A14ED)
        a = GG(a, b, c, d, x[k + 13], S21, 0xA9E3E905)
        d = GG(d, a, b, c, x[k + 2], S22, 0xFCEFA3F8)
        c = GG(c, d, a, b, x[k + 7], S23, 0x676F02D9)
        b = GG(b, c, d, a, x[k + 12], S24, 0x8D2A4C8A)

        a = HH(a, b, c, d, x[k + 5], S31, 0xFFFA3942)
        d = HH(d, a, b, c, x[k + 8], S32, 0x8771F681)
        c = HH(c, d, a, b, x[k + 11], S33, 0x6D9D6122)
        b = HH(b, c, d, a, x[k + 14], S34, 0xFDE5380C)
        a = HH(a, b, c, d, x[k + 1], S31, 0xA4BEEA44)
        d = HH(d, a, b, c, x[k + 4], S32, 0x4BDECFA9)
        c = HH(c, d, a, b, x[k + 7], S33, 0xF6BB4B60)
        b = HH(b, c, d, a, x[k + 10], S34, 0xBEBFBC70)
        a = HH(a, b, c, d, x[k + 13], S31, 0x289B7EC6)
        d = HH(d, a, b, c, x[k + 0], S32, 0xEAA127FA)
        c = HH(c, d, a, b, x[k + 3], S33, 0xD4EF3085)
        b = HH(b, c, d, a, x[k + 6], S34, 0x4881D05)
        a = HH(a, b, c, d, x[k + 9], S31, 0xD9D4D039)
        d = HH(d, a, b, c, x[k + 12], S32, 0xE6DB99E5)
        c = HH(c, d, a, b, x[k + 15], S33, 0x1FA27CF8)
        b = HH(b, c, d, a, x[k + 2], S34, 0xC4AC5665)

        a = II(a, b, c, d, x[k + 0], S41, 0xF4292244)
        d = II(d, a, b, c, x[k + 7], S42, 0x432AFF97)
        c = II(c, d, a, b, x[k + 14], S43, 0xAB9423A7)
        b = II(b, c, d, a, x[k + 5], S44, 0xFC93A039)
        a = II(a, b, c, d, x[k + 12], S41, 0x655B59C3)
        d = II(d, a, b, c, x[k + 3], S42, 0x8F0CCC92)
        c = II(c, d, a, b, x[k + 10], S43, 0xFFEFF47D)
        b = II(b, c, d, a, x[k + 1], S44, 0x85845DD1)
        a = II(a, b, c, d, x[k + 8], S41, 0x6FA87E4F)
        d = II(d, a, b, c, x[k + 15], S42, 0xFE2CE6E0)
        c = II(c, d, a, b, x[k + 6], S43, 0xA3014314)
        b = II(b, c, d, a, x[k + 13], S44, 0x4E0811A1)
        a = II(a, b, c, d, x[k + 4], S41, 0xF7537E82)
        d = II(d, a, b, c, x[k + 11], S42, 0xBD3AF235)
        c = II(c, d, a, b, x[k + 2], S43, 0x2AD7D2BB)
        b = II(b, c, d, a, x[k + 9], S44, 0xEB86D391)

        a = add_unsigned(a, AA)
        b = add_unsigned(b, BB)
        c = add_unsigned(c, CC)
        d = add_unsigned(d, DD)

    return (word_to_hex(a) + word_to_hex(b) + word_to_hex(c) + word_to_hex(d)).lower()
