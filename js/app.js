
window.console = Console('#console')

let monitor = Monitor('#monitor')
let leds = Leds('#leds')

let network = Network('#connection_state')
.listen('animation', Stats('#animation_stats'))
.listen('animation', leds.listener)
.listen('signals', Stats('#signals_stats'))
.listen('signals', monitor.listener)

monitor.sendto(network.sender)
