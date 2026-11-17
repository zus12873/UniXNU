// tablet-wifi-scan-probe.js [scan]: what CoreWLAN holds for each Wi-Fi scan result on the tablet, one line per network:
// channel, signal, whether it has a name, whether that name is a saved network (`known`), and the scan record's AGE,
// TIMESTAMP and flags. Prints no names and no addresses. A known network with a large AGE is one the list of networks shows
// although it is no longer in range.
// The lines are what CoreWiFi's CWFFilteredScanResults sees when it drops results (auto-join asks for a minimum signal, a
// maximum age and a minimum timestamp).
//
//   local-tools/tablet-ssh.py 'cat > /tmp/probe.js && osascript -l JavaScript /tmp/probe.js' < local-tools/tablet-wifi-scan-probe.js
//
// With `scan` it asks for a scan first (`osascript -l JavaScript /tmp/probe.js scan`); while the tablet is joined the driver
// answers that from the results it holds, after 2 s. Without it the results CoreWLAN has cached are printed, and a scan is
// asked for only when there are none.
ObjC.import('CoreWLAN');
function run(argv) {
  const out = [];
  const wifi = $.CWWiFiClient.sharedWiFiClient.interface;
  let set = argv.indexOf('scan') < 0 ? wifi.cachedScanResults : $();
  if (!set.isNil()) out.push('cached results: ' + set.count);
  if (set.isNil() || set.count == 0) {
    set = wifi.scanForNetworksWithNameError($(), $());
    out.push('scan results: ' + (set.isNil() ? 'nil' : set.count));
  }
  if (set.isNil()) return out.join('\n');
  const all = set.allObjects;
  const known = new Set();
  const profiles = wifi.configuration.networkProfiles;
  if (!profiles.isNil()) {
    const list = profiles.array;
    for (let k = 0; k < list.count; k++) { const name = list.objectAtIndex(k).ssid; if (!name.isNil()) known.add(ObjC.unwrap(name)); }
  }
  out.push('saved networks: ' + known.size);
  const keys = ['AGE', 'TIMESTAMP', 'RSSI', 'NOISE', 'CHANNEL', 'CHANNEL_FLAGS', 'CAPABILITIES', 'BEACON_INT', 'SCAN_RESULT_FROM_PROBE_RSP'];
  for (let k = 0; k < all.count; k++) {
    const net = all.objectAtIndex(k), ch = net.wlanChannel;
    let line = 'ch ' + ch.channelNumber + ' band ' + ch.channelBand + ' width ' + ch.channelWidth + ' rssi ' + net.rssiValue +
               ' noise ' + net.noiseMeasurement + ' name ' + (net.ssid.isNil() ? 'nil' : 'len ' + net.ssid.length) +
               ' known ' + (!net.ssid.isNil() && known.has(ObjC.unwrap(net.ssid)) ? 'yes' : 'no');
    if (!net.respondsToSelector('scanRecord')) line += ' | no scanRecord';
    else {
      const record = net.scanRecord;
      if (record.isNil()) line += ' | record nil';
      else {
        line += ' | record keys ' + record.count + ':';
        for (const key of keys) { const v = record.objectForKey(key); if (!v.isNil()) line += ' ' + key + '=' + ObjC.unwrap(v.description); }
        if (k == 0) line += ' | all keys: ' + ObjC.unwrap(record.allKeys.componentsJoinedByString(','));
      }
    }
    out.push(line);
  }
  return out.join('\n');
}
