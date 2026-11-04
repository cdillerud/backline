"""Responsive on-stage setlist acceptance with synthetic authenticated data."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from test_collaboration import accounts
from test_browser_collaboration import account_server,sign_in

@pytest.mark.parametrize("width",[320,390,1280])
def test_performance_view_large_type_and_running_order(account_server,accounts,width):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={"width":width,"height":780})
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        sign_in(page,account_server,"owner")
        page.evaluate("""() => {
          window.__wakeStats={requested:0,released:0};
          Object.defineProperty(navigator,'wakeLock',{configurable:true,value:{
            request:async()=>{
              window.__wakeStats.requested++;
              return {release:async()=>{window.__wakeStats.released++},addEventListener:()=>{}};
            }
          }});
        }""")
        page.evaluate("""() => {
          state.data.setlists = [{
            id: 900001,title:'Synthetic Gig Set',event_id:null,
            songs:[
              {id:1101,title:'Midnight Escape',song_key:'A',bpm:115},
              {id:1102,title:'Long Road Home',song_key:'E',bpm:96},
              {id:1103,title:'Encore',song_key:'D',bpm:125}
            ]
          }];
          openSetlistPerformance(900001);
        }""")
        stage=page.get_by_role("dialog",name="Performance view: Synthetic Gig Set")
        expect(stage.get_by_role("heading",name="Midnight Escape")).to_be_visible()
        expect(stage.get_by_text("Long Road Home",exact=True)).to_be_visible()
        stage.get_by_role("button",name="Increase stage font size").click()
        assert stage.evaluate("(el)=>Number(el.style.getPropertyValue('--stage-font-scale'))")>1
        stage.get_by_role("button",name="Keep screen awake").click()
        expect(stage.get_by_role("button",name="Allow screen sleep")).to_be_visible()
        assert page.evaluate("window.__wakeStats.requested")==1
        stage.get_by_role("button",name="Allow screen sleep").click()
        expect(stage.get_by_role("button",name="Keep screen awake")).to_be_visible()
        assert page.evaluate("window.__wakeStats.released")==1
        stage.get_by_role("button",name="Keep screen awake").click()
        expect(stage.get_by_role("button",name="Allow screen sleep")).to_be_visible()
        stage.get_by_role("button",name="Show running order").click()
        order=stage.get_by_role("navigation",name="Setlist running order")
        expect(order.get_by_role("button",name="3. Encore")).to_be_visible()
        order.get_by_role("button",name="3. Encore").click()
        expect(stage.get_by_role("heading",name="Encore")).to_be_visible()
        expect(stage.get_by_text("End of set")).to_be_visible()
        stage.press("ArrowLeft")
        expect(stage.get_by_role("heading",name="Long Road Home")).to_be_visible()
        stage.press("ArrowRight")
        expect(stage.get_by_role("heading",name="Encore")).to_be_visible()
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        output=Path("artifacts/gigday");output.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(output/f"performance-{width}.png"),full_page=False)
        stage.get_by_role("button",name="Close performance view").click()
        expect(stage).to_have_count(0)
        expect.poll(lambda:page.evaluate("window.__wakeStats.released")).to_be(2)
        assert not errors,errors
        browser.close()
