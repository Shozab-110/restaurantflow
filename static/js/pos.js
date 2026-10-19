(() => {
  const products=JSON.parse(document.getElementById('pos-products').textContent);
  const initial=JSON.parse(document.getElementById('pos-initial-cart').textContent);
  const currency=JSON.parse(document.getElementById('pos-currency').textContent);
  const rates=JSON.parse(document.getElementById('pos-rates').textContent);
  const catalog=new Map(products.map(p=>[Number(p.id),p]));
  let cart=[];let category='all';
  for(const line of initial){const p=catalog.get(Number(line.id));const qty=Number(line.quantity);if(p && Number.isInteger(qty) && qty>0 && qty<=99)cart.push({id:p.id,quantity:qty,notes:String(line.notes||'').slice(0,500)});}
  const cents=value=>{const parts=String(value).split('.');return BigInt(parts[0])*100n+BigInt((parts[1]||'').padEnd(2,'0').slice(0,2));};
  const price=value=>`${currency} ${(value/100n).toLocaleString('en-PK')}.${String(value%100n).padStart(2,'0')}`;
  const make=(tag,cls,text)=>{const el=document.createElement(tag);el.className=cls||'';if(text!==undefined)el.textContent=text;return el;};
  function render(){
    const list=document.getElementById('cart-items');list.replaceChildren();let subtotal=0n;let count=0;
    cart.forEach((line,index)=>{const p=catalog.get(Number(line.id));const total=cents(p.price)*BigInt(line.quantity);subtotal+=total;count+=line.quantity;
      const row=make('div','cart-item'),top=make('div','cart-item-top'),info=make('div');info.append(make('h3','',p.name),make('div','cart-item-price',price(cents(p.price))));
      const remove=make('button','cart-item-remove','×');remove.type='button';remove.setAttribute('aria-label',`Remove ${p.name}`);remove.addEventListener('click',()=>{cart.splice(index,1);render();});top.append(info,remove);
      const bottom=make('div','cart-item-bottom'),control=make('div','qty-control');for(const [symbol,delta]of [['−',-1],['+',1]]){const b=make('button','',symbol);b.type='button';b.setAttribute('aria-label',`${delta===1?'Increase':'Decrease'} ${p.name} quantity`);b.addEventListener('click',()=>{line.quantity=Math.min(99,line.quantity+delta);if(line.quantity<=0)cart.splice(index,1);render();});control.append(b);if(delta===-1)control.append(make('span','',String(line.quantity)));}bottom.append(control,make('strong','cart-item-total',price(total)));
      const notes=make('input');notes.type='text';notes.placeholder='Special instructions…';notes.maxLength=500;notes.value=line.notes;notes.setAttribute('aria-label',`Instructions for ${p.name}`);notes.addEventListener('input',()=>{line.notes=notes.value;sync();});row.append(top,bottom,notes);list.append(row);
    });
    const base=cents(rates.subtotal)-cents(rates.discount)+subtotal;
    const tax=(base*cents(rates.tax)+5000n)/10000n, service=(base*cents(rates.service)+5000n)/10000n;
    document.getElementById('cart-tax').textContent=price(tax-cents(rates.old_tax));
    document.getElementById('cart-service').textContent=price(service-cents(rates.old_service));
    document.getElementById('cart-total').textContent=price(base+tax+service);
    document.getElementById('cart-subtotal').textContent=price(subtotal);document.getElementById('cart-count').textContent=String(count);document.getElementById('cart-empty').hidden=cart.length>0;document.getElementById('submit-order').disabled=cart.length===0;sync();
  }
  function sync(){document.getElementById('cart-input').value=JSON.stringify(cart);}
  document.querySelectorAll('[data-product-id]').forEach(button=>button.addEventListener('click',()=>{const id=Number(button.dataset.productId);const match=cart.find(x=>Number(x.id)===id && !x.notes);if(match)match.quantity=Math.min(99,match.quantity+1);else cart.push({id,quantity:1,notes:''});render();}));
  function filter(){const search=document.getElementById('product-search').value.toLowerCase();let found=0;document.querySelectorAll('[data-product-id]').forEach(el=>{const show=(category==='all'||el.dataset.category===category)&&el.dataset.search.includes(search);el.hidden=!show;if(show)found++;});document.getElementById('no-products').hidden=found>0;}
  document.querySelectorAll('[data-category].category-tab').forEach(button=>button.addEventListener('click',()=>{category=button.dataset.category;document.querySelectorAll('.category-tab').forEach(el=>el.classList.toggle('active',el===button));filter();}));document.getElementById('product-search').addEventListener('input',filter);
  document.getElementById('pos-form').addEventListener('submit',event=>{if(!cart.length){event.preventDefault();window.alert('Add at least one item.');}sync();});
  const type=document.getElementById('id_order_type');function orderFields(){if(!type)return;const dine=type.value==='dine_in',delivery=type.value==='delivery';for(const id of ['id_table','id_delivery_address']){const el=document.getElementById(id);el.closest('.field').hidden=id==='id_table'?!dine:!delivery;el.disabled=id==='id_table'?!dine:!delivery;el.required=!el.disabled;}for(const id of ['id_customer_name','id_customer_phone'])document.getElementById(id).required=delivery;}type?.addEventListener('change',orderFields);orderFields();render();
})();
