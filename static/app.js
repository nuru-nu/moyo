
import { Console, h, Stats } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Monitor, Dump } from './smanmi/monitor.js'

import { Sonar, Css, AffectWordButtons, Debug, Cmd, Subsample, Midi, Actions, Transients, Image, Header } from './widgets.js'
import { Animations } from './animations.js'
import { Recorder } from './recorder.js'
import { Rec } from './recording.js'
import { Kinect } from './kinect.js'
import { Leds } from './leds.js'

fetch('/defs').then(resp => resp.json()).then(defs => {
  
  let monitor = Monitor('#monitor', defs)
  let leds = Leds('#leds', defs)
  
  const record_timestamps = true
  let network = Network('#connection_state', { record_timestamps })
  
  const sigels = Header('sig', h.div().of(
    h.div('console'),
    h.div('dump', {style: 'margin-top: 1rem;'}),
    h.div('transients'),
  )).into('#sig').els
  window.console = Console(sigels.console)
  Dump(sigels.dump, {network})
  Transients(sigels.transients, {network, defs})

  // Cmd('#cmd', {network, defs})
  Animations('#animation', { defs, network })
  Rec('#recording', {network})
  // Actions('#sound', { name: 'scene', values: defs.scenes, network })
  // Subsample('#subsample')
  // Sonar('#sonar', {network})
  Kinect('#kinect', {network})
  Css('#css', {network})
  AffectWordButtons('#cmd', {network})
  // Recorder('#recorder', {network, defs})
  let midi = Midi('#midi')
  Image('#kinect_image')

  network
  .listen('animation', Stats('#animation_stats'))
  .listen('animation', leds.listener)
  .listen('signals', Stats('#signals_stats'))
  .listenJson('signals', monitor.listener)
  .listenJson('signals', midi.listener)

  Debug('#debug', { network, record_timestamps })
  midi.sendto(network.sender)

})
