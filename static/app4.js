
import { Network } from './nurulib/network.js'
import { Css, ImageGPT, AffectWordButtons, AnimControl} from './widgets.js'
import { Dump } from './nurulib/monitor.js'
import { Leds } from './leds.js'

fetch('/defs').then(resp => resp.json()).then(defs => {  
  let leds = Leds('#leds', defs)
  const network = Network(null, {secondary: true})
  const sz = 0.33 * Math.min(window.innerWidth, window.innerHeight)
  ImageGPT('#image', {
    network,
    headless: true,
  })
  Css('#css', {
    network,
    readonly: true,
    headless: true,
    hidestate: true,
    width: sz, height: sz,
  })
  AffectWordButtons('#affectwords', {network, defs})
  Dump("#signals", {network})
  AnimControl('#anim_control', {network, defs})
  network
  .listen('animation', leds.listener)
})

document.addEventListener('gesturestart', function (e) {
  e.preventDefault();
});
