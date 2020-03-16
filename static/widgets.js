import { h, u, colors, Lines } from './smanmi/util.js'

export const Sonar = (output) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sonar'),
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
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('debug'),
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}

export const Recorder = (output) => {
  const disp = h.div({class: 'flex'}).of(
    'recorder',
    h.div().of(
      h.div('recording', {class: 'flex'}).of(
      ),
      h.div('playback', {class: 'flex'}).of(
      ),
    ),
  ).into(output).els
}

export const Cmd = (output) => {
  const cont = h.div().into(output).el
  fetch('/setstates').then(res => res.json()).then(setstates => {
    let {colors, states} = setstates
    colors.unshift('')
    states.unshift('')
    const fcs = [0, 1, 2, 3]
    let disp = h.div({class: 'flex widget'}).of(
      h.div({class: 'header'}).of('cmd'),
      h.div({class: 'flex'}).of(
        'fc',
        h.select('fc').of(fcs.map(value =>
          h.option({value}).of(value))),
        'color',
        h.select('color').of(colors.map(value =>
          h.option({value}).of(value))),
        'state',
        h.select('state').of(states.map(value =>
          h.option({value}).of(value))),
      ),
    ).into(cont).els

    disp.fc.addEventListener('change', e => {
      sender({fc: e.target.value === '' ? null : parseInt(e.target.value)})
    })
    disp.color.addEventListener('change', e => {
      const color = e.target.value === '' ? null : e.target.value
      sender({setstate: { color }})
    })
    disp.state.addEventListener('change', e => {
      const state = e.target.value === '' ? null : e.target.value
      sender({setstate: { state }})
    })
  })

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}
