"""Executable regressions for Rail Departures + Steam Train's single admin card."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ADMIN = (Path(__file__).resolve().parents[1] / "simulator" / "admin.html").read_text(encoding="utf-8")


def js_slice(start, end):
    return ADMIN.split(start, 1)[1].split(end, 1)[0]


class CombinedRailAdminTests(unittest.TestCase):
    def run_js(self, source):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for executable admin regression tests")
        completed = subprocess.run(
            [node, "-e", source], capture_output=True, text=True, check=True, timeout=20
        )
        return json.loads(completed.stdout)

    def test_single_card_contains_both_feeds_and_one_apply_action(self):
        rail_functions = "function railHealth(config,status){" + js_slice(
            "function railHealth(config,status){", "function queueMemberIds(){"
        )
        source = """
const fieldHtml=(id,field)=>'<input data-test-field="'+id+'.'+field+'">';
const advancedHtml=(id)=>'<span data-test-advanced="'+id+'"></span>';
const formatTime=()=> 'Never';
const escapeHtml=(v)=>String(v);
const cardHtml=()=>{throw Error('Two separate cards must not be rendered')};
""" + rail_functions + """
const config={
 feeds:{
  departures:{enabled:true,poll_seconds:120,screen_duration_seconds:20},
  steam_train:{enabled:true,animation_speed:35,words:'choo choo'}
 },
 schema:{feeds:{
  departures:{mutable_fields:['enabled','poll_seconds','screen_duration_seconds'],
              fields:{},advanced_fields:[]},
  steam_train:{mutable_fields:['enabled','animation_speed','words'],
               fields:{},advanced_fields:[]}
 }}
};
const status={feeds:{departures:{health:'ok'},steam_train:{health:'stale'}}};
const html=departuresSectionHtml(config,status);
const health=[railHealth(config,null),railHealth(config,status)];
config.feeds.steam_train.enabled=false;
health.push(railHealth(config,status));
console.log(JSON.stringify({html,health}));
"""
        result = self.run_js(source)
        html = result["html"]
        self.assertEqual(html.count("<article"), 1)
        self.assertEqual(html.count('class="card rail-card"'), 1)
        self.assertIn('data-feed="departures"', html)
        self.assertIn('data-rail-feed="departures"', html)
        self.assertIn('data-rail-feed="steam_train"', html)
        self.assertIn('data-test-field="steam_train.animation_speed"', html)
        self.assertIn('data-test-field="steam_train.words"', html)
        self.assertIn('data-test-field="steam_train.enabled"', html)
        self.assertIn('data-test-field="departures.poll_seconds"', html)
        self.assertIn('data-test-advanced="steam_train"', html)
        self.assertEqual(html.count("data-save-rail"), 1)
        self.assertNotIn("data-save-queue", html)
        self.assertEqual(result["health"], ["unavailable", "stale", "ok"])

    def test_both_feed_patches_are_collected_with_correct_field_ownership(self):
        functions = "function collectFeedFields(feedId,root){" + js_slice(
            "function collectFeedFields(feedId,root){", "function collectQueueCard(card){"
        )
        source = """
const WINDOW_UNITS=[['minutes',1],['hours',60],['days',1440],['weeks',10080],['months',43200]];
const state={config:{schema:{feeds:{
 departures:{label:'Rail',mutable_fields:['enabled','poll_seconds','schedule_windows'],
  fields:{enabled:{type:'boolean'},poll_seconds:{type:'number',minimum:60,maximum:86400}}},
 steam_train:{label:'Steam Train',mutable_fields:['enabled','animation_speed','words'],
  fields:{enabled:{type:'boolean'},animation_speed:{type:'number',minimum:1,maximum:300},
   words:{type:'string',maximumLength:80}}}
}}}};
const selectedFor=()=>[];
const values={
 departures:{enabled:{type:'checkbox',checked:true},poll_seconds:{value:'180'}},
 steam_train:{enabled:{type:'checkbox',checked:false},animation_speed:{value:'42'},
              words:{value:'Choo!'}}
};
const row={querySelector:(selector)=>({
 '[data-window-cron]':{value:'0 18 * * 1-5'},
 '[data-window-duration]':{value:'2'},
 '[data-window-unit]':{value:'hours'}
}[selector])};
const card={querySelector:(selector)=>{
 const id=selector.includes('steam_train')?'steam_train':'departures';
 return {querySelector:(fieldSelector)=>fieldSelector.startsWith('[data-schedule-windows')
   ? {querySelectorAll:()=>[row]}
   : values[id][fieldSelector.match(/data-field="([^"]+)"/)[1]]};
}};
""" + functions + """
console.log(JSON.stringify(collectRailCard(card)));
"""
        patches = self.run_js(source)
        self.assertEqual([pair[0] for pair in patches], ["departures", "steam_train"])
        self.assertEqual(
            patches[0][1],
            {"enabled": True, "poll_seconds": 180,
             "schedule_windows": [{"cron": "0 18 * * 1-5", "duration_minutes": 120}]},
        )
        self.assertEqual(
            patches[1][1],
            {"enabled": False, "animation_speed": 42, "words": "Choo!"},
        )

    def test_grouped_apply_preserves_draft_when_second_patch_fails(self):
        function = "async function saveRailCard(card){" + js_slice(
            "async function saveRailCard(card){", "async function saveQueueCard(card){"
        )
        source = """
let calls=[],notice='',renderCount=0,dirtyCount=0,restored=false;
const button={disabled:false,textContent:'Apply rail changes'};
const card={querySelector:(selector)=>selector==='[data-save-rail]'?button:null};
const captureDirtyDrafts=(id)=>{calls.push('capture:'+id);return {unrelated:{}};};
const collectRailCard=()=>[['departures',{enabled:true}],['steam_train',{words:'Choo!'}]];
const clearNotice=()=>{};
const showNotice=(message,kind)=>{notice=kind+':'+message;};
const patchFeed=async(id,body)=>{
 calls.push(id);
 if(id==='steam_train')throw Error('Configuration changed elsewhere (412)');
 return {rebuild_triggered:true};
};
const markDirty=()=>{dirtyCount++;};
const statusAfterSave=async()=>true;
const render=()=>{renderCount++;};
const restoreDirtyDrafts=()=>{restored=true;};
""" + function + """
saveRailCard(card).then(()=>console.log(JSON.stringify({
 calls,notice,renderCount,dirtyCount,restored,
 enabled:button.disabled,buttonText:button.textContent
})));
"""
        result = self.run_js(source)
        self.assertEqual(result["calls"], ["capture:departures", "departures", "steam_train"])
        self.assertIn("Some rail settings were saved", result["notice"])
        self.assertIn("412", result["notice"])
        self.assertEqual(result["renderCount"], 0)
        self.assertEqual(result["dirtyCount"], 1)
        self.assertFalse(result["restored"])
        self.assertFalse(result["enabled"])
        self.assertEqual(result["buttonText"], "Apply rail changes")

    def test_grouped_apply_validates_all_feeds_before_patching(self):
        self.assertIn("const patches=collectRailCard(card);", ADMIN)
        self.assertIn("for(const [feedId,body] of patches)", ADMIN)
        self.assertIn("const data=await patchFeed(feedId,body);", ADMIN)
        self.assertIn("const drafts=captureDirtyDrafts('departures');", ADMIN)
        self.assertIn("card.dataset.railGroup==='true'?['departures','steam_train']", ADMIN)
        self.assertIn("input.closest('[data-rail-feed]')?.dataset.railFeed", ADMIN)
        self.assertIn("card.querySelector('[data-rail-feed=\"'+CSS.escape(entry.feedId)+'\"]')", ADMIN)
        self.assertIn("card.querySelector('.rail-card", ADMIN)


if __name__ == "__main__":
    unittest.main()
