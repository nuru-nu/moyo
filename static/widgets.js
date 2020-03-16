import { h, u, colors, Lines } from './smanmi/util.js'

export const Sonar = (output) => {
  const disp = h.div({class: 'flex'}).of(
    'sonar',
    h.button('override').of('override'),
    h.input('sonar', {type: 'range', min: -1, max: 50, value: 50}),
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    disp.override.classList.toggle('on')
    disp.sonar.style.display = override ? 'block' : 'none'
    update()
  })
  disp.sonar.addEventListener('change', update)

  let sender
  function update() {
    if (!override) {
      console.log('sonar', null)
      if (sender) sender({sonar: null})
      return
    }
    if (sender) sender({sonar: parseInt(disp.sonar.value)})
    console.log('sonar', disp.sonar.value)
  }
  function listener(data) {
    if (override) return
    if (data.sonarsig) disp.sonar.value = 100 * data.sonarsig
  }
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Debug = (output, { network, record_timestamps }) => {
  const disp = h.div().of(
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}
