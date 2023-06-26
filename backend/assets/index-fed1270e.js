(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const r of document.querySelectorAll('link[rel="modulepreload"]'))l(r);new MutationObserver(r=>{for(const s of r)if(s.type==="childList")for(const a of s.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&l(a)}).observe(document,{childList:!0,subtree:!0});function n(r){const s={};return r.integrity&&(s.integrity=r.integrity),r.referrerPolicy&&(s.referrerPolicy=r.referrerPolicy),r.crossOrigin==="use-credentials"?s.credentials="include":r.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function l(r){if(r.ep)return;r.ep=!0;const s=n(r);fetch(r.href,s)}})();function D(){}function Ne(t){return t()}function Ce(){return Object.create(null)}function ee(t){t.forEach(Ne)}function Le(t){return typeof t=="function"}function Ee(t,e){return t!=t?e==e:t!==e||t&&typeof t=="object"||typeof t=="function"}function Be(t){return Object.keys(t).length===0}function y(t,e){t.appendChild(e)}function J(t,e,n){t.insertBefore(e,n||null)}function T(t){t.parentNode&&t.parentNode.removeChild(t)}function Xe(t,e){for(let n=0;n<t.length;n+=1)t[n]&&t[n].d(e)}function M(t){return document.createElement(t)}function x(t){return document.createElementNS("http://www.w3.org/2000/svg",t)}function re(t){return document.createTextNode(t)}function A(){return re(" ")}function Ye(){return re("")}function W(t,e,n,l){return t.addEventListener(e,n,l),()=>t.removeEventListener(e,n,l)}function f(t,e,n){n==null?t.removeAttribute(e):t.getAttribute(e)!==n&&t.setAttribute(e,n)}function He(t){return Array.from(t.childNodes)}function Pe(t,e){e=""+e,t.data!==e&&(t.data=e)}function me(t,e,n,l){n==null?t.style.removeProperty(e):t.style.setProperty(e,n,l?"important":"")}function se(t,e,n){t.classList[n?"add":"remove"](e)}let ie;function le(t){ie=t}function Te(){if(!ie)throw new Error("Function called outside component initialization");return ie}function Ie(t){Te().$$.on_mount.push(t)}const Z=[],Me=[];let $=[];const ze=[],Ge=Promise.resolve();let _e=!1;function qe(){_e||(_e=!0,Ge.then(Ae))}function he(t){$.push(t)}const de=new Set;let Q=0;function Ae(){if(Q!==0)return;const t=ie;do{try{for(;Q<Z.length;){const e=Z[Q];Q++,le(e),De(e.$$)}}catch(e){throw Z.length=0,Q=0,e}for(le(null),Z.length=0,Q=0;Me.length;)Me.pop()();for(let e=0;e<$.length;e+=1){const n=$[e];de.has(n)||(de.add(n),n())}$.length=0}while(Z.length);for(;ze.length;)ze.pop()();_e=!1,de.clear(),le(t)}function De(t){if(t.fragment!==null){t.update(),ee(t.before_update);const e=t.dirty;t.dirty=[-1],t.fragment&&t.fragment.p(t.ctx,e),t.after_update.forEach(he)}}function Je(t){const e=[],n=[];$.forEach(l=>t.indexOf(l)===-1?e.push(l):n.push(l)),n.forEach(l=>l()),$=e}const oe=new Set;let q;function Ke(){q={r:0,c:[],p:q}}function Re(){q.r||ee(q.c),q=q.p}function L(t,e){t&&t.i&&(oe.delete(t),t.i(e))}function F(t,e,n,l){if(t&&t.o){if(oe.has(t))return;oe.add(t),q.c.push(()=>{oe.delete(t),l&&(n&&t.d(1),l())}),t.o(e)}else l&&l()}function I(t){t&&t.c()}function Y(t,e,n,l){const{fragment:r,after_update:s}=t.$$;r&&r.m(e,n),l||he(()=>{const a=t.$$.on_mount.map(Ne).filter(Le);t.$$.on_destroy?t.$$.on_destroy.push(...a):ee(a),t.$$.on_mount=[]}),s.forEach(he)}function H(t,e){const n=t.$$;n.fragment!==null&&(Je(n.after_update),ee(n.on_destroy),n.fragment&&n.fragment.d(e),n.on_destroy=n.fragment=null,n.ctx=[])}function Ue(t,e){t.$$.dirty[0]===-1&&(Z.push(t),qe(),t.$$.dirty.fill(0)),t.$$.dirty[e/31|0]|=1<<e%31}function Fe(t,e,n,l,r,s,a,h=[-1]){const d=ie;le(t);const o=t.$$={fragment:null,ctx:[],props:s,update:D,not_equal:r,bound:Ce(),on_mount:[],on_destroy:[],on_disconnect:[],before_update:[],after_update:[],context:new Map(e.context||(d?d.$$.context:[])),callbacks:Ce(),dirty:h,skip_bound:!1,root:e.target||d.$$.root};a&&a(o.root);let _=!1;if(o.ctx=n?n(t,e.props||{},(i,u,...p)=>{const v=p.length?p[0]:u;return o.ctx&&r(o.ctx[i],o.ctx[i]=v)&&(!o.skip_bound&&o.bound[i]&&o.bound[i](v),_&&Ue(t,i)),u}):[],o.update(),_=!0,ee(o.before_update),o.fragment=l?l(o.ctx):!1,e.target){if(e.hydrate){const i=He(e.target);o.fragment&&o.fragment.l(i),i.forEach(T)}else o.fragment&&o.fragment.c();e.intro&&L(t.$$.fragment),Y(t,e.target,e.anchor,e.customElement),Ae()}le(d)}class je{$destroy(){H(this,1),this.$destroy=D}$on(e,n){if(!Le(n))return D;const l=this.$$.callbacks[e]||(this.$$.callbacks[e]=[]);return l.push(n),()=>{const r=l.indexOf(n);r!==-1&&l.splice(r,1)}}$set(e){this.$$set&&!Be(e)&&(this.$$.skip_bound=!0,this.$$set(e),this.$$.skip_bound=!1)}}const ce="";function Qe(){let t=Math.floor(Math.random()*256)+70,e=Math.floor(Math.random()*256)+70,n=Math.floor(Math.random()*256)+70,l="rgb("+t+", "+e+", "+n+")";document.body.style.background=l}function fe(t){fetch(`${ce}/state`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(t)}).then(e=>e.json()).then(e=>{console.log("Success:",e)}).catch(e=>{console.error("Error:",e),alert("Error:"+e)})}const ae=parseFloat;function ge(t,e=";"){let n;if(Array.isArray(t))n=t.filter(l=>l);else{n=[];for(const l in t)t[l]&&n.push(`${l}:${t[l]}`)}return n.join(e)}function We(t,e,n,l){let r,s;const a="1em";let h,d,o,_="-.125em";const i="visible";return l&&(o="center",s="1.25em"),n&&(r=n),e&&(e=="lg"?(d="1.33333em",h=".75em",_="-.225em"):e=="xs"?d=".75em":e=="sm"?d=".875em":d=e.replace("x","em")),ge([ge({float:r,width:s,height:a,"line-height":h,"font-size":d,"text-align":o,"vertical-align":_,"transform-origin":"center",overflow:i}),t])}function Ze(t,e,n,l,r,s=1,a="",h=""){let d=1,o=1;return r&&(r=="horizontal"?d=-1:r=="vertical"?o=-1:d=o=-1),ge([`translate(${ae(e)*s}${a},${ae(n)*s}${a})`,`scale(${d*ae(t)},${o*ae(t)})`,l&&`rotate(${l}${h})`]," ")}function Ve(t){let e,n,l,r,s,a,h,d;function o(u,p){return typeof u[10][4]=="string"?$e:xe}let _=o(t),i=_(t);return{c(){e=x("svg"),n=x("g"),l=x("g"),i.c(),f(l,"transform",t[12]),f(n,"transform",r="translate("+t[10][0]/2+" "+t[10][1]/2+")"),f(n,"transform-origin",s=t[10][0]/4+" 0"),f(e,"id",a=t[1]||void 0),f(e,"class",h="svelte-fa "+t[0]+" svelte-1cj2gr0"),f(e,"style",t[11]),f(e,"viewBox",d="0 0 "+t[10][0]+" "+t[10][1]),f(e,"aria-hidden","true"),f(e,"role","img"),f(e,"xmlns","http://www.w3.org/2000/svg"),se(e,"pulse",t[4]),se(e,"spin",t[3])},m(u,p){J(u,e,p),y(e,n),y(n,l),i.m(l,null)},p(u,p){_===(_=o(u))&&i?i.p(u,p):(i.d(1),i=_(u),i&&(i.c(),i.m(l,null))),p&4096&&f(l,"transform",u[12]),p&1024&&r!==(r="translate("+u[10][0]/2+" "+u[10][1]/2+")")&&f(n,"transform",r),p&1024&&s!==(s=u[10][0]/4+" 0")&&f(n,"transform-origin",s),p&2&&a!==(a=u[1]||void 0)&&f(e,"id",a),p&1&&h!==(h="svelte-fa "+u[0]+" svelte-1cj2gr0")&&f(e,"class",h),p&2048&&f(e,"style",u[11]),p&1024&&d!==(d="0 0 "+u[10][0]+" "+u[10][1])&&f(e,"viewBox",d),p&17&&se(e,"pulse",u[4]),p&9&&se(e,"spin",u[3])},d(u){u&&T(e),i.d()}}}function xe(t){let e,n,l,r,s,a,h,d,o,_;return{c(){e=x("path"),a=x("path"),f(e,"d",n=t[10][4][0]),f(e,"fill",l=t[6]||t[2]||"currentColor"),f(e,"fill-opacity",r=t[9]!=!1?t[7]:t[8]),f(e,"transform",s="translate("+t[10][0]/-2+" "+t[10][1]/-2+")"),f(a,"d",h=t[10][4][1]),f(a,"fill",d=t[5]||t[2]||"currentColor"),f(a,"fill-opacity",o=t[9]!=!1?t[8]:t[7]),f(a,"transform",_="translate("+t[10][0]/-2+" "+t[10][1]/-2+")")},m(i,u){J(i,e,u),J(i,a,u)},p(i,u){u&1024&&n!==(n=i[10][4][0])&&f(e,"d",n),u&68&&l!==(l=i[6]||i[2]||"currentColor")&&f(e,"fill",l),u&896&&r!==(r=i[9]!=!1?i[7]:i[8])&&f(e,"fill-opacity",r),u&1024&&s!==(s="translate("+i[10][0]/-2+" "+i[10][1]/-2+")")&&f(e,"transform",s),u&1024&&h!==(h=i[10][4][1])&&f(a,"d",h),u&36&&d!==(d=i[5]||i[2]||"currentColor")&&f(a,"fill",d),u&896&&o!==(o=i[9]!=!1?i[8]:i[7])&&f(a,"fill-opacity",o),u&1024&&_!==(_="translate("+i[10][0]/-2+" "+i[10][1]/-2+")")&&f(a,"transform",_)},d(i){i&&T(e),i&&T(a)}}}function $e(t){let e,n,l,r;return{c(){e=x("path"),f(e,"d",n=t[10][4]),f(e,"fill",l=t[2]||t[5]||"currentColor"),f(e,"transform",r="translate("+t[10][0]/-2+" "+t[10][1]/-2+")")},m(s,a){J(s,e,a)},p(s,a){a&1024&&n!==(n=s[10][4])&&f(e,"d",n),a&36&&l!==(l=s[2]||s[5]||"currentColor")&&f(e,"fill",l),a&1024&&r!==(r="translate("+s[10][0]/-2+" "+s[10][1]/-2+")")&&f(e,"transform",r)},d(s){s&&T(e)}}}function et(t){let e,n=t[10][4]&&Ve(t);return{c(){n&&n.c(),e=Ye()},m(l,r){n&&n.m(l,r),J(l,e,r)},p(l,[r]){l[10][4]?n?n.p(l,r):(n=Ve(l),n.c(),n.m(e.parentNode,e)):n&&(n.d(1),n=null)},i:D,o:D,d(l){n&&n.d(l),l&&T(e)}}}function tt(t,e,n){let{class:l=""}=e,{id:r=""}=e,{style:s=""}=e,{icon:a}=e,{size:h=""}=e,{color:d=""}=e,{fw:o=!1}=e,{pull:_=""}=e,{scale:i=1}=e,{translateX:u=0}=e,{translateY:p=0}=e,{rotate:v=""}=e,{flip:O=!1}=e,{spin:S=!1}=e,{pulse:g=!1}=e,{primaryColor:w=""}=e,{secondaryColor:b=""}=e,{primaryOpacity:C=1}=e,{secondaryOpacity:te=.4}=e,{swapOpacity:j=!1}=e,E,ne,V;return t.$$set=c=>{"class"in c&&n(0,l=c.class),"id"in c&&n(1,r=c.id),"style"in c&&n(13,s=c.style),"icon"in c&&n(14,a=c.icon),"size"in c&&n(15,h=c.size),"color"in c&&n(2,d=c.color),"fw"in c&&n(16,o=c.fw),"pull"in c&&n(17,_=c.pull),"scale"in c&&n(18,i=c.scale),"translateX"in c&&n(19,u=c.translateX),"translateY"in c&&n(20,p=c.translateY),"rotate"in c&&n(21,v=c.rotate),"flip"in c&&n(22,O=c.flip),"spin"in c&&n(3,S=c.spin),"pulse"in c&&n(4,g=c.pulse),"primaryColor"in c&&n(5,w=c.primaryColor),"secondaryColor"in c&&n(6,b=c.secondaryColor),"primaryOpacity"in c&&n(7,C=c.primaryOpacity),"secondaryOpacity"in c&&n(8,te=c.secondaryOpacity),"swapOpacity"in c&&n(9,j=c.swapOpacity)},t.$$.update=()=>{t.$$.dirty&16384&&n(10,E=a&&a.icon||[0,0,"",[],""]),t.$$.dirty&237568&&n(11,ne=We(s,h,_,o)),t.$$.dirty&8126464&&n(12,V=Ze(i,u,p,v,O,512))},[l,r,d,S,g,w,b,C,te,j,E,ne,V,s,a,h,o,_,i,u,p,v,O]}class nt extends je{constructor(e){super(),Fe(this,e,tt,et,Ee,{class:0,id:1,style:13,icon:14,size:15,color:2,fw:16,pull:17,scale:18,translateX:19,translateY:20,rotate:21,flip:22,spin:3,pulse:4,primaryColor:5,secondaryColor:6,primaryOpacity:7,secondaryOpacity:8,swapOpacity:9})}}const G=nt;var lt={prefix:"fas",iconName:"forward-step",icon:[320,512,["step-forward"],"f051","M52.5 440.6c-9.5 7.9-22.8 9.7-34.1 4.4S0 428.4 0 416V96C0 83.6 7.2 72.3 18.4 67s24.5-3.6 34.1 4.4l192 160L256 241V96c0-17.7 14.3-32 32-32s32 14.3 32 32V416c0 17.7-14.3 32-32 32s-32-14.3-32-32V271l-11.5 9.6-192 160z"]},rt=lt,it={prefix:"fas",iconName:"volume-low",icon:[448,512,[128264,"volume-down"],"f027","M301.1 34.8C312.6 40 320 51.4 320 64V448c0 12.6-7.4 24-18.9 29.2s-25 3.1-34.4-5.3L131.8 352H64c-35.3 0-64-28.7-64-64V224c0-35.3 28.7-64 64-64h67.8L266.7 40.1c9.4-8.4 22.9-10.4 34.4-5.3zM412.6 181.5C434.1 199.1 448 225.9 448 256s-13.9 56.9-35.4 74.5c-10.3 8.4-25.4 6.8-33.8-3.5s-6.8-25.4 3.5-33.8C393.1 284.4 400 271 400 256s-6.9-28.4-17.7-37.3c-10.3-8.4-11.8-23.5-3.5-33.8s23.5-11.8 33.8-3.5z"]},st=it,ft={prefix:"fas",iconName:"circle-play",icon:[512,512,[61469,"play-circle"],"f144","M0 256a256 256 0 1 1 512 0A256 256 0 1 1 0 256zM188.3 147.1c-7.6 4.2-12.3 12.3-12.3 20.9V344c0 8.7 4.7 16.7 12.3 20.9s16.8 4.1 24.3-.5l144-88c7.1-4.4 11.5-12.1 11.5-20.5s-4.4-16.1-11.5-20.5l-144-88c-7.4-4.5-16.7-4.7-24.3-.5z"]},at=ft,ot={prefix:"fas",iconName:"circle-pause",icon:[512,512,[62092,"pause-circle"],"f28b","M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM224 192V320c0 17.7-14.3 32-32 32s-32-14.3-32-32V192c0-17.7 14.3-32 32-32s32 14.3 32 32zm128 0V320c0 17.7-14.3 32-32 32s-32-14.3-32-32V192c0-17.7 14.3-32 32-32s32 14.3 32 32z"]},ct=ot,ut={prefix:"fas",iconName:"volume-high",icon:[640,512,[128266,"volume-up"],"f028","M533.6 32.5C598.5 85.3 640 165.8 640 256s-41.5 170.8-106.4 223.5c-10.3 8.4-25.4 6.8-33.8-3.5s-6.8-25.4 3.5-33.8C557.5 398.2 592 331.2 592 256s-34.5-142.2-88.7-186.3c-10.3-8.4-11.8-23.5-3.5-33.8s23.5-11.8 33.8-3.5zM473.1 107c43.2 35.2 70.9 88.9 70.9 149s-27.7 113.8-70.9 149c-10.3 8.4-25.4 6.8-33.8-3.5s-6.8-25.4 3.5-33.8C475.3 341.3 496 301.1 496 256s-20.7-85.3-53.2-111.8c-10.3-8.4-11.8-23.5-3.5-33.8s23.5-11.8 33.8-3.5zm-60.5 74.5C434.1 199.1 448 225.9 448 256s-13.9 56.9-35.4 74.5c-10.3 8.4-25.4 6.8-33.8-3.5s-6.8-25.4 3.5-33.8C393.1 284.4 400 271 400 256s-6.9-28.4-17.7-37.3c-10.3-8.4-11.8-23.5-3.5-33.8s23.5-11.8 33.8-3.5zM301.1 34.8C312.6 40 320 51.4 320 64V448c0 12.6-7.4 24-18.9 29.2s-25 3.1-34.4-5.3L131.8 352H64c-35.3 0-64-28.7-64-64V224c0-35.3 28.7-64 64-64h67.8L266.7 40.1c9.4-8.4 22.9-10.4 34.4-5.3z"]},mt=ut,dt={prefix:"fas",iconName:"backward-step",icon:[320,512,["step-backward"],"f048","M267.5 440.6c9.5 7.9 22.8 9.7 34.1 4.4s18.4-16.6 18.4-29V96c0-12.4-7.2-23.7-18.4-29s-24.5-3.6-34.1 4.4l-192 160L64 241V96c0-17.7-14.3-32-32-32S0 78.3 0 96V416c0 17.7 14.3 32 32 32s32-14.3 32-32V271l11.5 9.6 192 160z"]},_t=dt,ht={prefix:"fas",iconName:"music",icon:[512,512,[127925],"f001","M499.1 6.3c8.1 6 12.9 15.6 12.9 25.7v72V368c0 44.2-43 80-96 80s-96-35.8-96-80s43-80 96-80c11.2 0 22 1.6 32 4.6V147L192 223.8V432c0 44.2-43 80-96 80s-96-35.8-96-80s43-80 96-80c11.2 0 22 1.6 32 4.6V200 128c0-14.1 9.3-26.6 22.8-30.7l320-96c9.7-2.9 20.2-1.1 28.3 5z"]};function Oe(t,e,n){const l=t.slice();return l[14]=e[n],l}function Se(t){let e,n,l=t[14].substring(0,Math.max(0,t[14].length-4))+"",r,s,a,h;function d(){return t[9](t[14])}return{c(){e=M("li"),n=M("button"),r=re(l),s=A(),f(n,"class","song-list-item")},m(o,_){J(o,e,_),y(e,n),y(n,r),y(e,s),a||(h=W(n,"click",d),a=!0)},p(o,_){t=o,_&1&&l!==(l=t[14].substring(0,Math.max(0,t[14].length-4))+"")&&Pe(r,l)},d(o){o&&T(e),a=!1,h()}}}function gt(t){let e,n;return e=new G({props:{icon:ct,class:"fa fa-pause-circle fa-5x",size:"5x"}}),{c(){I(e.$$.fragment)},m(l,r){Y(e,l,r),n=!0},p:D,i(l){n||(L(e.$$.fragment,l),n=!0)},o(l){F(e.$$.fragment,l),n=!1},d(l){H(e,l)}}}function pt(t){let e,n;return e=new G({props:{icon:at,class:"fa fa-play-circle fa-5x",size:"5x"}}),{c(){I(e.$$.fragment)},m(l,r){Y(e,l,r),n=!0},p:D,i(l){n||(L(e.$$.fragment,l),n=!0)},o(l){F(e.$$.fragment,l),n=!1},d(l){H(e,l)}}}function yt(t){let e,n,l,r,s,a,h,d,o,_,i=t[1].substring(0,Math.max(0,t[1].length-4))+"",u,p,v,O,S,g,w,b,C,te,j,E,ne,V,c,pe,N,ye,K,R,ue,ve;r=new G({props:{icon:ht,style:"font-size: 1.8rem;"}});let U=t[0],k=[];for(let m=0;m<U.length;m+=1)k[m]=Se(Oe(t,U,m));S=new G({props:{icon:_t,class:"fa fa-step-backward fa-2x",size:"2x"}});const we=[pt,gt],B=[];function be(m,P){return m[2]?0:1}return b=be(t),C=B[b]=we[b](t),E=new G({props:{icon:rt,class:"fa fa-step-backward fa-2x",size:"2x"}}),c=new G({props:{icon:st,class:"fa fa-volume-down",size:"2.2x"}}),K=new G({props:{icon:mt,class:"fa fa-volume-up",size:"2.2x"}}),{c(){e=M("div"),n=M("div"),l=M("h2"),I(r.$$.fragment),s=re(" Music Player"),a=A(),h=M("ol");for(let m=0;m<k.length;m+=1)k[m].c();d=A(),o=M("div"),_=M("div"),u=re(i),p=A(),v=M("div"),O=M("div"),I(S.$$.fragment),g=A(),w=M("div"),C.c(),te=A(),j=M("div"),I(E.$$.fragment),ne=A(),V=M("div"),I(c.$$.fragment),pe=A(),N=M("input"),ye=A(),I(K.$$.fragment),me(l,"font-size","2rem"),f(l,"class","main-heading"),f(n,"class","songs-list"),f(_,"class","track-name text-center"),me(_,"text-align","center"),me(_,"font-weight","500"),f(o,"class","details"),f(O,"class","prev-track"),f(w,"class","playpause-track"),f(j,"class","next-track"),f(v,"class","buttons"),f(N,"type","range"),f(N,"min","0.00"),f(N,"max","1.00"),f(N,"step","0.01"),f(N,"class","volume_slider"),N.value=t[3],f(V,"class","slider_container"),f(e,"class","player")},m(m,P){J(m,e,P),y(e,n),y(n,l),Y(r,l,null),y(l,s),y(n,a),y(n,h);for(let X=0;X<k.length;X+=1)k[X]&&k[X].m(h,null);y(e,d),y(e,o),y(o,_),y(_,u),y(e,p),y(e,v),y(v,O),Y(S,O,null),y(v,g),y(v,w),B[b].m(w,null),y(v,te),y(v,j),Y(E,j,null),y(e,ne),y(e,V),Y(c,V,null),y(V,pe),y(V,N),y(V,ye),Y(K,V,null),R=!0,ue||(ve=[W(l,"click",t[4]),W(O,"click",t[10]),W(w,"click",t[5]),W(j,"click",t[11]),W(N,"change",t[7])],ue=!0)},p(m,[P]){if(P&65){U=m[0];let z;for(z=0;z<U.length;z+=1){const ke=Oe(m,U,z);k[z]?k[z].p(ke,P):(k[z]=Se(ke),k[z].c(),k[z].m(h,null))}for(;z<k.length;z+=1)k[z].d(1);k.length=U.length}(!R||P&2)&&i!==(i=m[1].substring(0,Math.max(0,m[1].length-4))+"")&&Pe(u,i);let X=b;b=be(m),b===X?B[b].p(m,P):(Ke(),F(B[X],1,1,()=>{B[X]=null}),Re(),C=B[b],C?C.p(m,P):(C=B[b]=we[b](m),C.c()),L(C,1),C.m(w,null)),(!R||P&8)&&(N.value=m[3])},i(m){R||(L(r.$$.fragment,m),L(S.$$.fragment,m),L(C),L(E.$$.fragment,m),L(c.$$.fragment,m),L(K.$$.fragment,m),R=!0)},o(m){F(r.$$.fragment,m),F(S.$$.fragment,m),F(C),F(E.$$.fragment,m),F(c.$$.fragment,m),F(K.$$.fragment,m),R=!1},d(m){m&&T(e),H(r),Xe(k,m),H(S),B[b].d(),H(E),H(c),H(K),ue=!1,ee(ve)}}}function vt(t,e,n){let l=[],r="",s=!1,a=0;const h=()=>{fetch(`${ce}/music_list`).then(g=>g.json()).then(g=>{n(0,l=g),console.log("Got music_list from server:",g)})},d=()=>{fetch(`${ce}/state`).then(g=>g.json()).then(g=>{n(1,r=g.fileName),n(2,s=g.isPaused),n(3,a=g.volume),console.log("Got state from server",g)})},o=()=>{fetch(`${ce}/reload_music_list`).then(g=>g.json()).then(g=>{h(),d()})},_=()=>{n(2,s=!s),fe(s?{pause:!0}:{resume:!0})},i=g=>{Qe(),n(1,r=g),fe({play:g}),n(2,s=!1)},u=g=>{let w=g.target.value;fe({volume:parseFloat(w)})},p=g=>{const w=l.indexOf(r);g=="next"?w==l.length-1?i(l[0]):i(l[w+1]):w==0?i(l[l.length-1]):i(l[w-1])};return Ie(()=>{h(),d()}),[l,r,s,a,o,_,i,u,p,g=>i(g),()=>p("prev"),()=>p("next")]}class wt extends je{constructor(e){super(),Fe(this,e,vt,yt,Ee,{})}}new wt({target:document.getElementById("app")});
