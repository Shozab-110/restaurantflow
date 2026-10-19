import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const html=readFileSync('.local/verified-pos.html','utf8');
function setup(){
  const dom=new JSDOM(html,{url:'http://127.0.0.1:8000/pos/',runScripts:'outside-only'});
  const w=dom.window;w.alert=()=>{};w.confirm=()=>true;
  w.eval(readFileSync('static/js/pos.js','utf8'));
  return {dom,w,d:w.document};
}
let passed=0;
function test(name,fn){const ctx=setup();try{fn(ctx);passed++;console.log('PASS',name);}finally{ctx.dom.window.close();}}
function cart(d){return JSON.parse(d.getElementById('cart-input').value);}
test('empty cart prevents checkout',({w,d})=>{
  assert.equal(d.getElementById('submit-order').disabled,true);
  const event=new w.Event('submit',{bubbles:true,cancelable:true});
  assert.equal(d.getElementById('pos-form').dispatchEvent(event),false);
});
test('product selection, quantities, and exact integer tax/service preview',({d})=>{
  const p=JSON.parse(d.getElementById('pos-products').textContent)[0];
  const button=d.querySelector(`[data-product-id="${p.id}"]`);button.click();button.click();
  assert.equal(cart(d)[0].quantity,2);
  const rates=JSON.parse(d.getElementById('pos-rates').textContent);
  const cents=v=>{const a=String(v).split('.');return BigInt(a[0])*100n+BigInt((a[1]||'').padEnd(2,'0'));};
  const base=cents(p.price)*2n;
  const expected=base+(base*cents(rates.tax)+5000n)/10000n+(base*cents(rates.service)+5000n)/10000n;
  const shown=d.getElementById('cart-total').textContent.replace(/[^0-9.]/g,'');
  assert.equal(cents(shown),expected);
  assert.equal(d.getElementById('submit-order').disabled,false);
  d.querySelector('[aria-label^="Decrease"]').click();assert.equal(cart(d)[0].quantity,1);
});
test('instructions persist and a second customization remains a separate line',({w,d})=>{
  const button=d.querySelector('[data-product-id]');button.click();
  const input=d.querySelector('.cart-item input');input.value='Severe peanut allergy <please check>';
  input.dispatchEvent(new w.Event('input',{bubbles:true}));
  button.click();assert.equal(cart(d).length,2);assert.equal(cart(d)[0].notes,'Severe peanut allergy <please check>');
  assert.equal(d.querySelectorAll('.cart-item').length,2);
  d.querySelector('.cart-item-remove').click();assert.equal(cart(d).length,1);
});
test('search and category filters select the actual rendered product cards',({w,d})=>{
  const input=d.getElementById('product-search');input.value='zz-no-such-item';input.dispatchEvent(new w.Event('input'));
  assert.equal(d.getElementById('no-products').hidden,false);
  assert.equal([...d.querySelectorAll('[data-product-id]')].filter(x=>!x.hidden).length,0);
  input.value='';input.dispatchEvent(new w.Event('input'));
  const category=d.querySelector('.category-tab[data-category]:not([data-category="all"])');category.click();
  const visible=[...d.querySelectorAll('[data-product-id]')].filter(x=>!x.hidden);
  assert.ok(visible.length>0);assert.ok(visible.every(x=>x.dataset.category===category.dataset.category));
});
test('delivery requires guest details and dine-in requires a table',({w,d})=>{
  const type=d.getElementById('id_order_type');type.value='delivery';type.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('id_table').disabled,true);
  for(const id of ['id_customer_name','id_customer_phone','id_delivery_address'])assert.equal(d.getElementById(id).required,true);
  type.value='dine_in';type.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('id_table').required,true);assert.equal(d.getElementById('id_table').disabled,false);
  assert.equal(d.getElementById('id_delivery_address').disabled,true);
});
console.log(`${passed} POS DOM interaction tests passed. These do not verify browser layout.`);
