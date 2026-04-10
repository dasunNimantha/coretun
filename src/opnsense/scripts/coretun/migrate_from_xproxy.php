#!/usr/local/bin/php
<?php

/*
 * Copyright (C) 2025 OPNsense Community
 * One-time migration: xproxy plugin config -> coretun naming.
 *
 * - Renames <OPNsense><xproxy> to <coretun>
 * - Renames <interfaces><xproxytun> to <coretun> if <coretun> does not exist
 * - Renames gateway name XPROXY_TUN -> CORETUN_TUN (MVC gateways)
 * - Renames gateway interface reference xproxytun -> coretun under OPNsense
 */

$configPath = getenv('OPNSENSE_CONFIG') ?: '/conf/config.xml';
if (!is_readable($configPath) || !is_writable($configPath)) {
    exit(0);
}

$dom = new DOMDocument();
$dom->preserveWhiteSpace = false;
$dom->formatOutput = false;
if (@$dom->load($configPath) === false) {
    fwrite(STDERR, "migrate_from_xproxy: failed to load config\n");
    exit(1);
}

$xpath = new DOMXPath($dom);
$changed = false;

/* OPNsense/xproxy -> coretun */
$legacy = $xpath->query('/opnsense/OPNsense/xproxy');
if ($legacy->length > 0) {
    $node = $legacy->item(0);
    $replacement = $dom->createElement('coretun');
    while ($node->firstChild) {
        $replacement->appendChild($node->firstChild);
    }
    foreach (iterator_to_array($node->attributes) as $attr) {
        $replacement->setAttribute($attr->name, $attr->value);
    }
    $node->parentNode->replaceChild($replacement, $node);
    $changed = true;
}

/* interfaces: xproxytun -> coretun */
$ifaces = $xpath->query('/opnsense/interfaces');
if ($ifaces->length > 0) {
    $interfaces = $ifaces->item(0);
    $old = null;
    foreach ($interfaces->childNodes as $child) {
        if ($child->nodeType === XML_ELEMENT_NODE && $child->localName === 'xproxytun') {
            $old = $child;
            break;
        }
    }
    if ($old !== null) {
        $hasCoretun = false;
        foreach ($interfaces->childNodes as $child) {
            if ($child->nodeType === XML_ELEMENT_NODE && $child->localName === 'coretun') {
                $hasCoretun = true;
                break;
            }
        }
        if (!$hasCoretun) {
            $new = $dom->createElement('coretun');
            while ($old->firstChild) {
                $new->appendChild($old->firstChild);
            }
            foreach (iterator_to_array($old->attributes) as $attr) {
                $new->setAttribute($attr->name, $attr->value);
            }
            $interfaces->replaceChild($new, $old);
            $changed = true;
        }
    }
}

/* MVC gateways: name and interface tags anywhere under OPNsense */
foreach ($xpath->query('//OPNsense//name') as $el) {
    if (trim($el->textContent) === 'XPROXY_TUN') {
        $el->textContent = 'CORETUN_TUN';
        $changed = true;
    }
}
foreach ($xpath->query('//OPNsense//interface') as $el) {
    if (trim($el->textContent) === 'xproxytun') {
        $el->textContent = 'coretun';
        $changed = true;
    }
}

if ($changed) {
    $dom->save($configPath);
}

exit(0);
