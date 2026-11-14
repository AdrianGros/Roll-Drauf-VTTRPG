// Explicit campaign management entry; no table context/session is created.
import { MapLibraryController } from './play-map-library.js';
let active;
export async function open(campaignId) {
    if (active?.busy) { active.dialog.focus(); return; }
    const data = await Auth.makeAuthRequest(`/api/campaigns/${campaignId}`);
    const campaign = data.campaign;
    if (!campaign || !(campaign.is_owner || ['DM','CO_DM'].includes(campaign.your_role))) throw new Error(globalThis.VTTUi('Nicht berechtigt.'));
    if (!document.querySelector('link[href="/static/css/project-library.css"]')) {
        const style = document.createElement('link');style.rel='stylesheet';style.href='/static/css/project-library.css';document.head.append(style);
    }
    active?.close();active?.dialog.remove();
    active = new MapLibraryController({ campaignId, auth:Auth }, {target:'campaign',onImported:async()=>{
        await BookScene.renderCampaignHubDetail(campaignId);
        document.getElementById('campaignHubMaps')?.scrollIntoView({block:'start'});
        BookScene.setCampaignHubStatus(globalThis.VTTUi('Karte zur Kampagne hinzugefügt.'));
    }});
    active.open();
}
