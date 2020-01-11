
window.console = Console('#console')

let monitor = Monitor('#monitor')
let leds = Leds('#leds')

let network = Network('#connection_state', { record_timestamps: true })
.listen('animation', Stats('#animation_stats'))
.listen('animation', leds.listener)
.listen('signals', Stats('#signals_stats'))
.listen('signals', monitor.listener)

monitor.sendto(network.sender)

const controls = h.div().of(
  h.button('download').of('download traces')
).into('#controls').els
controls.download.addEventListener('click', network.download_timestamps)

