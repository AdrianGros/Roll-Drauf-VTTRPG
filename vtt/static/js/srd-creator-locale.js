/* Source-pinned names only. Every choice, comparison and calculation uses canonical data. */
(function(){
    'use strict';
    const SC=window.SrdCreator, app=SC.app;
    const ui=(source,parameters={})=>window.VTTI18n.module().literal(source,parameters);
    const locale=()=>window.VTTI18n.contentLocale();
    const cached=new Map(), pending=new Map();
    let canonical=new Map();
    SC.buildDisplayIndex=function(data){
        canonical=new Map();
        for(const list of [data.classes,data.species,data.backgrounds,data.feats,data.classOptions,
            data.equipment.items,data.equipment.weapons,data.equipment.armor]){
            for(const entry of list)canonical.set(entry.id,entry);
        }
        for(const c of data.classes)for(const row of c.levels)for(const feature of row.features)canonical.set(feature.id,feature);
        for(const [id,entry] of Object.entries(data.spells))canonical.set(id,{id,...entry});
    };
    const overlay=()=>locale()==='en' && app.display?.canonicalHash===app.canonicalHash?app.display:null;
    function canonicalEntry(id){return canonical.get(id) || app.extras.subclasses?.[id];}
    SC.ruleName=function(value,fallback){
        const entry=typeof value==='string'?canonicalEntry(value):value;
        const id=typeof value==='string'?value:value?.id;
        const original=entry?.name ?? fallback ?? id ?? '';
        if(entry?.homebrew)return original;
        if(SC.L.skills?.[id])return SC.skillName(id);
        if(SC.L.langs?.[id])return SC.languageName(id);
        return overlay()?.names[id]?.name ?? original;
    };
    SC.nameLocale=function(value){
        const entry=typeof value==='string'?canonicalEntry(value):value;
        const id=typeof value==='string'?value:value?.id;
        if(entry?.homebrew)return undefined;
        if(SC.L.classes?.[id])return SC.nameLocale(SC.L.classes[id]);
        if(SC.L.abilities?.[id])return overlay()?.terms['abilities:'+id]?'en':'de';
        if(app.data?.alignments.some(item=>item.id===id))return overlay()?.terms['alignments:'+id]?'en':'de';
        if(overlay()?.names[id])return 'en';
        if(SC.L.skills?.[id])return overlay()?.terms['skills:'+id]?'en':'de';
        if(SC.L.langs?.[id])return overlay()?.terms['languages:'+id]?'en':'de';
        return entry || /^(?:classes|spells|feats|character-origins|equipment)\./.test(id || '')?'de':undefined;
    };
    SC.ruleLabel=(value,fallback)=>SC.h('bdi',{lang:SC.nameLocale(value)},SC.ruleName(value,fallback));
    function term(kind,id,fallback){return overlay()?.terms[kind+':'+id]?.name ?? fallback ?? id;}
    SC.skillName=id=>term('skills',id,SC.L.skills[id]?.name);
    SC.abilityName=id=>term('abilities',id,SC.L.abilities[id]?.name);
    SC.abilityAbbr=id=>overlay()?.terms['abilities:'+id]?.abbreviation ?? SC.L.abilities[id]?.abbreviation ?? id;
    SC.languageName=id=>term('languages',id,SC.L.langs[id]?.name);
    SC.alignmentName=id=>term('alignments',id,app.data.alignments.find(entry=>entry.id===id)?.name);
    SC.weaponMasteryName=name=>term('weaponMasteries',name,name);
    SC.weaponPropertyName=name=>term('weaponProperties',name,name);
    SC.coinAbbr=key=>overlay()?.terms['coins:'+key]?.abbreviation ?? key;
    // Species keys are scoped canonical identities. Authored homebrew is always literal.
    function speciesTerm(species,kind,key,fallback){
        return species.homebrew?fallback:term(kind,key,fallback);
    }
    SC.speciesTraitName=(species,name)=>speciesTerm(species,'speciesTraits',species.id+'/'+name,name);
    SC.speciesOptionName=(species,choice,option)=>speciesTerm(species,'speciesOptions',species.id+'/'+choice.id+'/'+option.id,option.name);
    SC.speciesSizeName=(species,size)=>speciesTerm(species,'sizes',size,size);
    SC.speciesCreatureTypeName=species=>speciesTerm(species,'creatureTypes',species.creatureType,species.creatureType);
    SC.speciesDamageTypeName=(species,name)=>speciesTerm(species,'damageTypes',name,name);
    SC.speciesLabelsLocale=species=>species.homebrew?undefined:(overlay()?'en':'de');
    SC.className=key=>SC.ruleName(SC.L.classes[key],key);
    SC.subclassName=id=>SC.ruleName(id,String(id).split('subclass-').pop().replace(/-/g,' '));
    SC.spellName=id=>SC.ruleName(id,app.data.spells[id]?.name);
    SC.itemName=id=>SC.ruleName(id,SC.L.items[id] || String(id).split('.').pop().replace(/-/g,' '));
    SC.featName=value=>SC.ruleName(SC.L.feats[value] || app.data.feats.find(entry=>entry.name===value),value);
    SC.refreshLocaleStatus=function(){
        const node=SC.$('scLocaleStatus');
        node.hidden=locale()!=='en' || app.localeState!=='fallback';
        node.textContent=node.hidden?'':ui('Die englischen Regelnamen konnten nicht geladen werden. Deutsche Namen werden angezeigt; dein Entwurf bleibt bearbeitbar.');
    };
    SC.loadLocale=async function(){
        const selected=locale(),seq=app.localeSeq=(app.localeSeq || 0)+1,hash=app.canonicalHash;
        if(selected==='de'){
            app.display=null;app.localeState='canonical';SC.refreshLocaleStatus();return true;
        }
        app.localeState='loading';
        try{
            if(!/^[a-f0-9]{64}$/.test(hash || ''))throw new Error('missing canonical version');
            { // Revalidate overlay-only corrections even when canonical mechanics did not change.
                if(!pending.has(hash))pending.set(hash,(async()=>{
                    const result=await SC.api('/creator-display?locale=en&v='+hash);
                    const value=result.data;
                    if(!result.ok || value.schemaVersion!==1 || value.locale!=='en' || value.canonicalHash!==hash ||
                        !value.names || !value.terms)throw new Error('display unavailable');
                    cached.set(hash,value);return value;
                })().finally(()=>pending.delete(hash)));
                await pending.get(hash);
            }
            if(seq!==app.localeSeq || selected!==locale())return false;
            app.display=cached.get(hash);app.localeState='ready';
        }catch(_){
            if(seq!==app.localeSeq || selected!==locale())return false;
            app.display=null;app.localeState='fallback';
        }
        SC.refreshLocaleStatus();return true;
    };
    SC.entrySource=function(id){
        const mapped=overlay()?.names[id];
        return mapped?{id:mapped.enEntityId,locale:'en',featureIds:mapped.featureIds,differences:mapped.sourceDifferences}:
            {id,locale:'de',fallback:locale()==='en'};
    };
})();
