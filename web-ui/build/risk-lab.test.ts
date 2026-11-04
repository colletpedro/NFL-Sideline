import {describe,it,expect} from 'vitest';
import {allowedLabRequest} from './risk-lab';
describe('local lab read boundary',()=>{
 const h={host:'127.0.0.1:18121','x-risk-lab':'1'};
 it('accepts only same-origin header-marked GET without a body',()=>{expect(allowedLabRequest('GET',h.host,h,18121)).toBe(true);for(const headers of [{...h,origin:'https://other.test'},{...h,'content-length':'1'},{...h,expect:'100-continue'},{...h,'transfer-encoding':'chunked'},{...h,'x-risk-lab':'0'}])expect(allowedLabRequest('GET',h.host,headers,18121)).toBe(false);expect(allowedLabRequest('POST',h.host,h,18121)).toBe(false);expect(allowedLabRequest('GET','localhost:18121',h,18121)).toBe(false);expect(allowedLabRequest('GET',h.host,h,18121,['Host',h.host,'Host',h.host])).toBe(false);});
});
