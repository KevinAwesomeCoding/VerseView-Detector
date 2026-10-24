'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {approvalDecision}=require('../notification-actions.cjs');

test('notification buttons preserve Approve and Deny across current and legacy Electron events',()=>{
  assert.equal(approvalDecision({actionIndex:0}),true);
  assert.equal(approvalDecision({actionIndex:1}),false);
  assert.equal(approvalDecision({},0),true);
  assert.equal(approvalDecision({},1),false);
  assert.equal(approvalDecision({actionIndex:-1}),null);
  assert.equal(approvalDecision({},undefined),null);
  assert.equal(approvalDecision({actionIndex:'0'}),null);
});
