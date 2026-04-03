"""Greasemonkey/Tampermonkey userscript content for MSAL token extraction."""

USERSCRIPT_JS = """\
// ==UserScript==
// @name         m365-cli Token Helper
// @namespace    m365-cli
// @version      1.7
// @description  Extracts MSAL tokens from Microsoft 365 apps and sends to m365-cli
// @match        https://teams.microsoft.com/*
// @match        https://outlook.office.com/*
// @match        https://outlook.office365.com/*
// @match        https://outlook.cloud.microsoft/*
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    const CALLBACK_URL = 'http://127.0.0.1:9365/callback';
    function log(msg) {
        console.log('[m365-cli] ' + msg);
    }

    function decodeJwtAudience(jwt) {
        try {
            const payload = jwt.split('.')[1];
            const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
            return { aud: decoded.aud || '', scp: decoded.scp || '', exp: decoded.exp };
        } catch(e) { return null; }
    }

    function findGraphToken() {
        const stores = [
            { name: 'sessionStorage', store: sessionStorage },
            { name: 'localStorage', store: localStorage }
        ];

        // Strategy 1: MSAL cache entries with accesstoken in key name
        for (const { name, store } of stores) {
            for (let i = 0; i < store.length; i++) {
                const key = store.key(i);
                if (!key.toLowerCase().includes('accesstoken') && !key.toLowerCase().includes('access_token')) continue;
                try {
                    const entry = JSON.parse(store.getItem(key));
                    const target = entry.target || '';
                    if (target.toLowerCase().includes('graph.microsoft.com')) {
                        const expiresOn = entry.expires_on || entry.expiresOn || entry.extended_expires_on;
                        const secret = entry.secret || entry.accessToken || entry.access_token;
                        if (secret && expiresOn) {
                            log('Found Graph token (strategy 1) in ' + name);
                            return { access_token: secret, expires_at: new Date(parseInt(expiresOn) * 1000).toISOString(), scopes: target };
                        }
                    }
                } catch(e) {}
            }
        }

        // Strategy 2: MSAL v2 — read token index keys like msal.2.token.keys.{clientId}
        for (const { name, store } of stores) {
            for (let i = 0; i < store.length; i++) {
                const key = store.key(i);
                if (!key.match(/^msal[.][0-9]+[.]token[.]keys[.]/)) continue;
                try {
                    const tokenKeys = JSON.parse(store.getItem(key));
                    log('MSAL v2 token index found in ' + name + ' with ' + (tokenKeys.accessToken || []).length + ' access tokens');
                    for (const tokenKey of (tokenKeys.accessToken || [])) {
                        const raw = store.getItem(tokenKey);
                        if (!raw) continue;
                        const entry = JSON.parse(raw);
                        const target = entry.target || '';
                        if (target.toLowerCase().includes('graph.microsoft.com')) {
                            const expiresOn = entry.expiresOn || entry.expires_on || entry.extended_expires_on;
                            const secret = entry.secret;
                            if (secret && expiresOn) {
                                log('Found Graph token (MSAL v2) scopes: ' + target.substring(0, 80));
                                return { access_token: secret, expires_at: new Date(parseInt(expiresOn) * 1000).toISOString(), scopes: target };
                            }
                        }
                    }
                } catch(e) { log('MSAL v2 parse error: ' + e); }
            }
        }

        log('No graph token found — dumping all ' + (sessionStorage.length + localStorage.length) + ' storage keys for debugging');
        for (const { name, store } of stores) {
            for (let i = 0; i < store.length; i++) {
                log(name + ': ' + store.key(i).substring(0, 80));
            }
        }
        return null;
    }

    function findTeamsToken() {
        // Teams uses the IC3 token (aud: ic3.teams.office.com) for chatsvc API calls
        const stores = [
            { name: 'sessionStorage', store: sessionStorage },
            { name: 'localStorage', store: localStorage }
        ];
        for (const { name, store } of stores) {
            for (let i = 0; i < store.length; i++) {
                const key = store.key(i);
                if (!key.toLowerCase().includes('accesstoken') && !key.toLowerCase().includes('access_token')) continue;
                try {
                    const entry = JSON.parse(store.getItem(key));
                    const target = entry.target || '';
                    if (target.toLowerCase().includes('ic3.teams.office.com')) {
                        const expiresOn = entry.expires_on || entry.expiresOn || entry.extended_expires_on;
                        const secret = entry.secret || entry.accessToken || entry.access_token;
                        if (secret && expiresOn) {
                            log('Found IC3 token (chatsvc)');
                            return { access_token: secret, expires_at: new Date(parseInt(expiresOn) * 1000).toISOString() };
                        }
                    }
                } catch(e) {}
            }
        }
        return null;
    }

    function sendToken() {
        const graphToken = findGraphToken();
        const teamsToken = findTeamsToken();

        if (!graphToken && !teamsToken) return;

        const payload = {};
        if (graphToken) {
            payload.access_token = graphToken.access_token;
            payload.expires_at = graphToken.expires_at;
            payload.scopes = graphToken.scopes;
        }
        if (teamsToken) {
            payload.teams_token = teamsToken.access_token;
            payload.teams_token_expires_at = teamsToken.expires_at;
            log('Including IC3/chatsvc token in payload');
        }

        log('Sending tokens to server');
        GM_xmlhttpRequest({
            method: 'POST',
            url: CALLBACK_URL,
            headers: { 'Content-Type': 'application/json' },
            data: JSON.stringify(payload),
            onload: function(resp) {
                log('Tokens sent successfully');
            },
            onerror: function(err) {
                // Server not running, ignore
            }
        });
    }

    // Fire on page load (with a short delay to let MSAL populate storage)
    setTimeout(sendToken, 3000);

    // Re-check every 30 seconds to catch token refreshes
    setInterval(sendToken, 30000);
})();
"""
