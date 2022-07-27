import { h, u, ui, observe } from './smanmi/util.js'

export const Header = (name, el) => {
  const ret = h.div({class: 'flex widget'}).of(
    h.div('header', {class: 'header', style: 'cursor:pointer'}).of(name),
    h.div('cont').of(el),
    h.div('placeholder', {class: 'h'}).of('...'),
  )
  const els = ret.els
  els.header.addEventListener('click', () => {
    els.cont.classList.toggle('h')
    els.placeholder.classList.toggle('h')
  })
  return ret
}

export const Sonar = (output, {network}) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sonar'),
    h.button('override').of('override'),
    h.input('sonar', {type: 'range', min: 0, max: 100, value: 100}),
    h.button('pir').of('pir'),
    h.button('pir_on .h').of('ON'),
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    update()
  })
  disp.sonar.addEventListener('input', update)

  let pir_override
  disp.pir.addEventListener('click', () => {
    network.sender({pir_override: pir_override === null ? 0 : null})
  })
  disp.pir_on.addEventListener('click', () => {
    network.sender({pir_override: 1 * !pir_override})
  })

  function update() {
    if (!override) {
      network.sender({sonar_override: null})
      return
    }
    network.sender({sonar_override: parseInt(disp.sonar.value) / 100})
  }
  network.listenJson('signals', function(data) {
    const sonar_override = data.hasOwnProperty('sonar_override') && data.sonar_override !== null
    if (sonar_override !== disp.override.classList.contains('on')) {
      disp.override.classList.toggle('on')
      disp.sonar.style.display = override ? 'block' : 'none'
    }
    disp.sonar.value = 100 * data.sonar
    if (pir_override !== data.pir_override) {
      pir_override = data.pir_override
      disp.pir.classList[pir_override === null ? 'remove' : 'add']('on')
      disp.pir_on.classList[pir_override !== null ? 'remove' : 'add']('h')
      disp.pir_on.classList[pir_override ? 'add' : 'remove']('on')
    }
  })
}

export const Debug = (output, { network, record_timestamps }) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('debug'),
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}

export const Subsample = (output, {network}) => {
  const subsamples = [1, 2, 5, 10, 15, 20, 30]
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('subsample'),
    h.div({class: 'flex'}).of(
      h.button('full', {class: 'on'}).of('full on'),
      h.div('controls', {style: 'display: none'}).of(
        'recorder', h.select('recorder').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
        'animator', h.select('animator').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
      ),
    ),
  ).into(output).els
  disp.recorder.value = disp.animator.value = 10

  let full = true
  disp.full.addEventListener('click', () => {
    full = !full
    disp.full.classList.toggle('on')
    disp.controls.style.display = full ? 'none' : 'block'
    update()
  })
  function update() {
    const subsample = full ? 1 : parseInt(disp.recorder.value)
    network.sender({ action: `subsample=${subsample}` })
  }
  disp.recorder.addEventListener('change', update)
  disp.animator.addEventListener('change', update)
}

export const Cmd = (output, {network, defs}) => {
  const actions = [
    'fc=0', 'fc=1', 'fc=2', 'fc=3', 'next',
    'growl=angry', 'sub=on', 'sub=off', 'growl=hole',
    'dream',
  ]
  const els = Header('cmd', h.div().of(
    ActionsButtons({name: 'mode', values: defs.modes, network}),
    h.div().of(
      actions.map(a => h.button(a).of(a)),
    ),
    'raw: ', h.input('raw', {type: 'text'}),
  )).into(output).els

  actions.forEach(action => els[action].addEventListener('click', () => {
    network.sender({ action })
  }))

  const lastraws = []
  let lastrawi = 0
  els.raw.addEventListener('keyup', e => {
    if (e.keyCode === 38 && lastrawi > 0) { // keyup
      e.target.value = lastraws[--lastrawi]
    }
    if (e.keyCode === 40 && lastrawi < lastraws.length - 1) { // keydown
      e.target.value = lastraws[++lastrawi]
    }
    if (e.keyCode === 13) {
      const [name, ...value] = e.target.value.split('=')
      network.sender({[name]: value.join('=')})
      if (lastraws.indexOf(e.target.value) === -1) {
        lastraws.push(e.target.value)
      }
      e.target.value = ''
      lastrawi = lastraws.length
    }
  })
}

export const Midi = (output) => {
  const notes = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
  ]
  const note_re = /(\d+): ([A-G]#?)(-?\d+) (.*)/
  const range_re = /^\d+:\sX\d+=\d+$/
  const channels = new Map()
  const keys = new Map()
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('midi'),
    ui.v(
      ui.h(
        'channel ',
        ui.choice('channel', {values: ['1', '2', '3', '4', '5']}),
        'octave ',
        ui.choice('octave', {values: ['0', '1', '2', '3', '4', '5'], initial: '2'}),
      ),
      notes.map(note => h.button(note).of(note)),
      h.div('cont'),
      ui.h(
        ui.choice('xchoice', {values: ['-', 'X1', 'X2', 'X3']}),
        ui.range('xrange'),
      )
    ),
  ).into(output).els

  let channel, octave
  disp.channel.change(value => channel = value).init()
  disp.octave.change(value => octave = value).init()
  function updatex(v) {
    const value = Math.round(parseFloat(v * 127))
    if (disp.xchoice.value !== '-') {
      sender({midi: `${channel}: ${disp.xchoice.value}=${value}`})
    }
  }
  disp.xchoice.change(updatex)
  disp.xrange.change(updatex)

  notes.forEach(note => {
    disp[note].addEventListener('mousedown', function() {
      this.classList.add('on')
      sender({midi: `${channel}: ${note}${octave} on`})
    })
    disp[note].addEventListener('mouseup', function() {
      this.classList.remove('on')
      sender({midi: `${channel}: ${note}${octave} off`})
    })
  })

  function value(note) {
    const octave = parseInt(note.substr(note.length - 1))
    const idx = notes.indexOf(note.substr(0, note.length - 1))
    return octave * 12 + idx
  }
  function sort(cont) {
    const arr = Array.from(cont.children).map(child => [
      value(child.textContent), child])
    while (cont.firstChild) cont.removeChild(cont.firstChild)
    arr.sort()
    arr.forEach(idx_child => cont.appendChild(idx_child[1]))
  }

  function listener(signals) {
    if (!signals.midi) return
    if (range_re.exec(signals.midi)) return
    const m = note_re.exec(signals.midi)
    if (m === null) {
      console.warn('Could not parse signals.midi', signals.midi)
      return
    }
    let [_, channel, letter, octave, command] = m
    if (!channels.has(channel)) {
      channels.set(channel, ui.h(
        `${channel}:`,
        h.div('cont'),
      ).into(disp.cont).els.cont)
    }
    const key = `${channel}:${letter}${octave}`
    if (!keys.has(key)) {
      keys.set(
        key, h.span('.key').of(
          `${letter}${octave}`,
        ).into(channels.get(channel)).el)
      sort(channels.get(channel))
    }
    if (command === 'on') {
      keys.get(key).classList.add('on')
    } else if (command === 'off') {
      keys.get(key).classList.remove('on')
    }
  }

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Css = (output, {network, readonly, headless, width, height, hidestate}) => {
  width = width || 200
  height = height || 200
  const xlim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const ylim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const r = width / 25
  const disp = h.div({class: 'flex widget'}).of(
    headless ? [] : h.div({class: 'header'}).of('css'),
    ui.v(
      readonly ? [] : h.div().of(
        h.button('clear').of('clear'),
        ' α=',
        h.input('alpha', {type: 'range', min: 5, max: 100, value: 10}),
      ),
      h.canvas('xy .css', {width, height}),
      h.div('state', {style: 'text-align:center'}),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  if (!readonly) {
    disp.clear.addEventListener('click', () => network.sender({target_css: null}))
    disp.alpha.addEventListener('input', e => {
      network.sender({css_alpha: parseFloat(e.target.value)})
    })
    disp.xy.addEventListener('click', e => {
      network.sender({target_css: [fromx(e.offsetX), fromy(e.offsetY)]})
    })
  }

  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => xlim[0] + x / width * (xlim[1] - xlim[0])
  const fromy = y => ylim[0] + (height - y) / height * (ylim[1] - ylim[0])

  function background(css) {
    var font_height = Math.floor(height / 20)
    var font = `${font_height}px Arial`
    var font2 = `${font_height * 1.5}px Arial`

    ctx.lineWidth = 1
    ctx.strokeStyle = ctx.fillStyle = 'white'
    ctx.font = font
    ctx.globalAlpha = 0.2
    if (css[0] < -0.25 && css[1] > 0){
      ctx.globalAlpha = 1
    }
    ctx.fillStyle = 'red' // Angry
    ctx.fillRect(tox(-1), toy(1), tox(-0.25), toy(0))

    ctx.globalAlpha = 0.2
    if (css[0] > 0.25 && css[1] > 0){
      ctx.globalAlpha = 1
    }
    ctx.fillStyle = '#7b03fc' // Happy
    ctx.fillRect(tox(0.25), toy(1), tox(-0.25), toy(0))

    ctx.globalAlpha = 0.2
    if (css[0] > -0.25 && css[0] < 0.25 && css[1] > 0){
      ctx.globalAlpha = 1
    }
    ctx.fillStyle = '#ebc034' // Calm
    ctx.fillRect(tox(-0.25), toy(1), tox(-0.5), toy(0))

    ctx.globalAlpha = 0.2
    if (css[0] > -0.5 && css[0] < 0.5 && css[1] < -0.5){
      ctx.globalAlpha = 1
    }
    ctx.fillStyle = 'gray' // Sleeping
    ctx.fillRect(tox(-0.5), toy(-0.5), tox(0), toy(-1))
    ctx.globalAlpha = 1
    
    ctx.strokeStyle = ctx.fillStyle = '#bababa'
    ctx.beginPath()
    ctx.moveTo(0, height/2)
    ctx.lineTo(width, height/2)
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2, height)
    ctx.closePath()

    // Arrow Heads
    const darr = height / 30
    var x =  width / 2 - ctx.measureText("High").width - font_height / 2
    ctx.fillText("High", x, 2* darr + font_height / 2);
    ctx.fillText("Arousal", width / 2 + font_height / 2, 2* darr + font_height / 2);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2-darr, darr)
    ctx.lineTo(width/2+darr, darr)
    ctx.closePath()
    ctx.fill()

    var x =  width / 2 - ctx.measureText("Low").width - font_height / 2
    ctx.fillText("Low", x, height - darr - font_height / 2);
    ctx.fillText("Arousal", width / 2 + font_height / 2, height - darr - font_height / 2);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width/2, height)
    ctx.lineTo(width/2-darr, height-darr)
    ctx.lineTo(width/2+darr, height-darr)
    ctx.closePath()
    ctx.fill()

    var x =  (width / 2 - ctx.measureText("Negative").width) / 2
    ctx.fillText("Negative", width / 8, height / 2 + 3*font_height / 3);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(0, height/2)
    ctx.lineTo(darr, height/2-darr)
    ctx.lineTo(darr, height/2+darr)
    ctx.closePath()
    ctx.fill()

    var x =  (width / 2 - ctx.measureText("Positive").width) / 2 + width / 2 
    ctx.fillText("Positive", x, height / 2 + 3*font_height / 3);
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width, height/2)
    ctx.lineTo(width-darr, height/2-darr)
    ctx.lineTo(width-darr, height/2+darr)
    ctx.closePath()
    ctx.fill()

    ctx.stroke()

    ctx.font = font2
    ctx.strokeStyle = ctx.fillStyle = 'white'
    var emo_width = (tox(-0.25) - tox(-1))
    var x = (emo_width - ctx.measureText("Angry").width) / 2
    ctx.fillText("Angry", x, height / 4 + font_height/3);
    var x = width - ((emo_width - ctx.measureText("Happy").width) / 2 + ctx.measureText("Happy").width)
    ctx.fillText("Happy", x, height / 4 + font_height/3);
    ctx.fillText("Calm", width / 2 - ctx.measureText("Calm").width / 2, height / 4 + font_height/3);
    ctx.fillText("Sleep", width / 2 - ctx.measureText("Sleep").width / 2,  7  *height / 8);

  }

  network.listenJson('signals', function listener(data) {
    ctx.clearRect(0, 0, width, height)
    const { target_css, css, css_alpha } = data
    background(css)

    if (target_css) {
      ctx.strokeStyle = '#f00'
      ctx.lineWidth = Math.max(2, width / 100)
      ctx.beginPath()
      ctx.arc(tox(target_css[0]), toy(target_css[1]), r * 1.4, 0, 2 * Math.PI)
      ctx.stroke()
    }
    if (css) {
      ctx.fillStyle = '#0f0'
      ctx.beginPath()
      ctx.arc(tox(css[0]), toy(css[1]), r, 0, 2 * Math.PI)
      ctx.fill()
    }
    if (!readonly && css_alpha) disp.alpha.value = css_alpha

    if (data.mode == 'one' && data.state_one && !hidestate) {
      const s = data.state_one
      disp.state.textContent = `one: ${s.state} (t=${Math.floor(s.timer)})`
    }

    if (data.mode == 'kosmos' && data.state_kosmos && !hidestate) {
      const s = data.state_kosmos
      const t1 = Math.floor(Math.max(0, data.state_kosmos.timer))
      const t2 = Math.floor(Math.max(0, data.state_kosmos.sonar_timer))
      const t3 = Math.floor(Math.max(0, data.state_kosmos.log_timer))
      let t = `${t1}`
      if (t2) t += `,s=${t2}`
      if (t3) t += `,l=${t3}`
      disp.state.textContent = `kosmos: ${s.state} (${t})`
    }
  })
}

export const ActionsButtons = ({name, values, network}) => {
  let value = null
  const els = h.div('cont').of(
    ui.hw(
      values.map(s => h.button(s).of(s))
    )
  ).els
  values.forEach(s => {
    els[s].addEventListener('click', () => {
      network.sender({action: `${name}=${s}`})
    })
  })
  network.listenJson('signals', data => {
    const v = data[name]
    if (v && v != value) {
      if (value && els[value]) {
        els[value].classList.remove('on')
      }
      if (els[v]) els[v].classList.add('on')
      value = v
    }
  })
  return els.cont
}

export const Actions = (output, {name, values, network}) => {
  h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of(name),
    ActionsButtons({name, values, network})
  ).into(output)
}

export const Transients = (output, {network, defs}) => {

  const limit = 100
  let include = [], exclude = [], paused = false
  const transients = defs.monitor_def.transients
  const disp = h.div().of(
    ui.h(
      'transients - filter:',
      h.input('include', {type: 'text'}), '\\',
      h.input('exclude', {type: 'text', value: 'heart'}),
      h.button('reset').of('reset'),
      h.button('clear').of('clear'),
      ui.toggle('pause').change(value => paused = value),
    ),
    h.div('.scrollable').of(h.div('output')),
  ).into(output).els

  update()

  const matches = s => (
    !include.length || include.some(token => s.search(token) >= 0)
  ) && (
    !exclude.length || exclude.every(token => s.search(token) == -1)
  )
  function update() {
    include = disp.include.value.split(/\s+/g).filter(x => x !== '')
    exclude = disp.exclude.value.split(/\s+/g).filter(x => x !== '')
    Array.from(disp.output.children).forEach(el => 
      el.classList[matches(el.textContent) ? 'remove' : 'add']('h'))
  }
  disp.include.addEventListener('change', update)
  disp.exclude.addEventListener('change', update)
  disp.reset.addEventListener('click', () => {
    disp.include.value = disp.exclude.value = ''
    include = exclude = []
    update()
  })
  disp.clear.addEventListener('click', () => {
    u.empty(disp.output)
  })

  const value_length = 30
  function listener(data) {
    if (paused) return
    let now = new Date().toTimeString().substr(0, 9)
    transients.forEach(transient => {
      if (data[transient] && data[transient].length !== 0) {
        let value = ('' + data[transient]).replace('\n', '\\n')
        if (value.length > value_length) value = value.substr(0, value_length - 3) + '...'
        const text = `${now} ${transient}: ${value}`
        const el = h.div().of(text).el
        if (!matches(text)) el.classList.add('h')
        disp.output.insertBefore(el, disp.output.firstChild)
        while (disp.output.children.length > limit) {
          disp.output.removeChild(disp.output.lastChild)
        }
      }
    })
  }

  network.listenJson('signals', listener)
}

export const Image = (output, refresh_secs) => {
  refresh_secs = refresh_secs || .5
  const disp = h.div('cont').of(
    h.img('img'),
  ).into(output).els
  disp.img.src = '/kinect'
  let id = window.setTimeout(refresh, 1e3 * refresh_secs)
  function refresh() {
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
    disp.img.src = '/kinect?' + new Date().getTime()
  }
  observe(disp.cont).start(() => {
    console.log('start')
    id = window.setTimeout(refresh, 1e3 * refresh_secs)
  }).stop(() => {
    console.log('stop')
    if (id) window.clearTimeout(id)
    id = null
  })
}
