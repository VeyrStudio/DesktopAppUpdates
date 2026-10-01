const test=require('node:test');
const assert=require('node:assert/strict');
const {versionGreater}=require('../src/updater');
test('The Index update version comparator isolates older and equal versions',()=>{
 assert.equal(versionGreater('0.1.1','0.1.0'),true);
 assert.equal(versionGreater('0.1.10','0.1.9'),true);
 assert.equal(versionGreater('0.1.9','0.1.10'),false);
 assert.equal(versionGreater('0.1.0','0.1.0'),false);
 assert.equal(versionGreater('0.1.99','0.2.1'),false);
 assert.equal(versionGreater('1.0.0','0.99.999'),true);
 assert.equal(versionGreater('1.2.3','1.3.0'),false);
});
