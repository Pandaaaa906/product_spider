/**
 *
 * @param: arg1 String 初次请求得到的页面有一个arg1的变量，获取该变量后传入getAcwScV2即可获得acw_sc__v2
 * @description: 使用阿里反扒的网站，cookie中需要带有acw_sc__v2
 */

var _0x5e8b26 = '3000176000856006061501533003690027800375'

var getAcwScV2 = function (arg1) {
    String['prototype']['hexXor'] = function (_0x4e08d8) {
        var _0x5a5d3b = '';
        for (var _0xe89588 = 0x0; _0xe89588 < this['length'] && _0xe89588 < _0x4e08d8['length']; _0xe89588 += 0x2) {
            var _0x401af1 = parseInt(this['slice'](_0xe89588, _0xe89588 + 0x2), 0x10);
            var _0x105f59 = parseInt(_0x4e08d8['slice'](_0xe89588, _0xe89588 + 0x2), 0x10);
            var _0x189e2c = (_0x401af1 ^ _0x105f59)['toString'](0x10);
            if (_0x189e2c['length'] == 0x1) {
                _0x189e2c = '0' + _0x189e2c;
            }
            _0x5a5d3b += _0x189e2c;
        }
        return _0x5a5d3b;
    };
    String['prototype']['unsbox'] = function () {
        var _0x4b082b = [0xf, 0x23, 0x1d, 0x18, 0x21, 0x10, 0x1, 0x26, 0xa, 0x9, 0x13, 0x1f, 0x28, 0x1b, 0x16, 0x17, 0x19, 0xd, 0x6, 0xb, 0x27, 0x12, 0x14, 0x8, 0xe, 0x15, 0x20, 0x1a, 0x2, 0x1e, 0x7, 0x4, 0x11, 0x5, 0x3, 0x1c, 0x22, 0x25, 0xc, 0x24];
        var _0x4da0dc = [];
        var _0x12605e = '';
        for (var i = 0; i < this['length']; i++) {
            //execjs 环境中不能用下标取单个字符
            var temp = this.charAt(i);
            for (var j = 0; j < _0x4b082b['length']; j++) {
                if (_0x4b082b[j] == i + 1) {
                    _0x4da0dc[j] = temp;
                }
            }
        }
        _0x12605e = _0x4da0dc['join']('');
        return _0x12605e;
    };
    var _0x23a392 = arg1['unsbox']();
    return _0x23a392['hexXor'](_0x5e8b26)
};