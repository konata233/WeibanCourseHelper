import CryptoJS from 'crypto-js';

/**
 * 简化的去抖函数(debounce),具体功能参考underscore库对应函数_.debounce
 * @param {Function} fn - 待执行函数
 * @param {Number} ms - 多少区间内去抖（毫秒）
 * @returns {Function} - 包装后函数
 */
export const debounce = (fn, ms = 500) => {
  let timer;
  const clearTimer = () => {
    clearTimeout(timer);
    timer = null;
  };

  return function (...params) {
    if (timer) {
      clearTimer();
    }
    timer = setTimeout(() => {
      fn.apply(this, [...params]);
      clearTimer();
    }, ms);
  };
};

export const formatDate = (fmt, timestamp) => {
  const date = new Date(timestamp);
  let ret;
  const opt = {
    'y+': date.getFullYear().toString(),
    'M+': (date.getMonth() + 1).toString(),
    'd+': date.getDate().toString(),
    'h+': date.getHours().toString(),
    'm+': date.getMinutes().toString(),
    's+': date.getSeconds().toString()
  };
  for (const k in opt) {
    // if (Object.hasOwn(opt, k)) {
    // object.hasOwnProperty(property)
    if (Object.hasOwnProperty.call(opt, k)) {
      ret = new RegExp('(' + k + ')').exec(fmt);
      if (ret) {
        fmt = fmt.replace(ret[1], (ret[1].length === 1) ? (opt[k]) : (opt[k].padStart(ret[1].length, '0')));
      }
    }
  }
  return fmt;
};

export const setWeChatTitle = (title) => {
  document.title = title;

  const mobile = navigator.userAgent.toLowerCase();
  if (/iphone|ipad|ipod/.test(mobile)) {
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    // 替换成站标favicon路径或者任意存在的较小的图片即可
    iframe.setAttribute('src', '');
    const iframeCallback = function () {
      setTimeout(function () {
        iframe.removeEventListener('load', iframeCallback);
        document.body.removeChild(iframe);
      }, 0);
    };

    iframe.addEventListener('load', iframeCallback);
    document.body.appendChild(iframe);
  }
};

const initKey = 'xie2gg';
const keySize = 128;

/**
 * 生成密钥字节数组, 原始密钥字符串不足128位, 补填0.
 * @param {string} key - 原始 key 值
 * @return Buffer
 */
const fillKey = (key) => {
  const filledKey = Buffer.alloc(keySize / 8);
  const keys = Buffer.from(key);
  if (keys.length < filledKey.length) {
    filledKey.forEach((b, i) => { filledKey[i] = keys[i]; });
  }

  return filledKey;
};

/**
 * 定义加密函数
 * @param {string} data - 需要加密的数据, 传过来前先进行 JSON.stringify(data);
 * @param {string} key - 加密使用的 key
 */
export const aesEncrypt = (data, key) => {
  /**
   * CipherOption, 加密的一些选项:
   *   mode: 加密模式, 可取值(CBC, CFB, CTR, CTRGladman, OFB, ECB), 都在 CryptoJS.mode 对象下
   *   padding: 填充方式, 可取值(Pkcs7, AnsiX923, Iso10126, Iso97971, ZeroPadding, NoPadding), 都在 CryptoJS.pad 对象下
   *   iv: 偏移量, mode === ECB 时, 不需要 iv
   * 返回的是一个加密对象
   */
  const cipher = CryptoJS.AES.encrypt(data, key, {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
    iv: ''
  });

  // 将加密后的数据转换成 Base64
  const base64Cipher = cipher.ciphertext.toString(CryptoJS.enc.Base64);

  // 处理 Android 某些低版的BUG
  const resultCipher = base64Cipher.replace(/\+/g, '-').replace(/\//g, '_');

  // 返回加密后的经过处理的 Base64
  return resultCipher;
};

// 获取填充后的key
// 注意，明文、秘钥和偏移向量一般先用诸如 CryptoJS.enc.Utf8.parse() 转成 WordArray 对象再传入，这样做得到结果与不转换直接传入是不一样的。
export const key = CryptoJS.enc.Utf8.parse(fillKey(initKey));



// WEBPACK FOOTER //
// ./src/utils/util-functions.js