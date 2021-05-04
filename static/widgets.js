import { h, u, ui, observe } from './smanmi/util.js'

export const Header = (name, el) => {
  const ret = h.div({class: 'flex widget', style: 'cursor:pointer'}).of(
    h.div('header', {class: 'header'}).of(name),
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
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    update()
  })
  disp.sonar.addEventListener('input', update)

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
    network.sender({
      'recorder': {
        subsample: full ? 1 : parseInt(disp.recorder.value),
      },
      'animator': {
        subsample: full ? 1 : parseInt(disp.animator.value),
      },
    })
  }
  disp.recorder.addEventListener('change', update)
  disp.animator.addEventListener('change', update)
}

export const Cmd = (output, {network}) => {
  const actions = [
    'fc=0', 'fc=1', 'fc=2', 'fc=3', 'rnca=next', 'state=sleep',
  ]
  let els = h.div('cont', {class: 'flex widget'}).of(
    h.div({class: 'header'}).of('cmd'),
    h.div().of(
      actions.map(a => h.button(a).of(a)),
      h.input('input', {type: 'text'}),
    ),
  ).into(output).els

  actions.forEach(action => els[action].addEventListener('click', () => {
    network.sender({ action })
  }))

  // els.sel.addEventListener('change', e => {
  //   network.sender({action: e.target.value})
  //   els.sel.value = ''
  // })

  els.input.addEventListener('keyup', e => {
    if (e.keyCode === 13) {
      network.sender({ action: e.target.value })
      e.target.value = ''
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
        ui.choice('channel', {values: ['1', '2', '3', '4']}),
        'octave ',
        ui.choice('octave', {values: ['0', '1', '2', '3', '4'], initial: '2'}),
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
  function updatex() {
    const value = Math.round(parseFloat(disp.xrange.value * 127))
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

export const Css = (output, {network}) => {
  const width = 200
  const height = 200
  const xlim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const ylim = [-1, 1]  // Note: assumed [-1, 1] by background() below ...
  const r = 8
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('css'),
    ui.v(
      h.div().of(
        h.button('clear').of('clear'),
        ' α=',
        h.input('alpha', {type: 'range', min: 5, max: 100, value: 10}),
      ),
      h.canvas('xy .css', {width, height}),
    ),
  ).into(output).els
  const ctx = disp.xy.getContext('2d')

  disp.clear.addEventListener('click', () => network.sender({target_css: null}))
  disp.alpha.addEventListener('input', e => {
    network.sender({css_alpha: parseFloat(e.target.value)})
  })

  const tox = x => width  * (x - xlim[0]) / (xlim[1] - xlim[0])
  const toy = y => height - height * (y - ylim[0]) / (ylim[1] - ylim[0])
  const fromx = x => xlim[0] + x / width * (xlim[1] - xlim[0])
  const fromy = y => ylim[0] + (height - y) / height * (ylim[1] - ylim[0])

  disp.xy.addEventListener('click', e => {
    network.sender({target_css: [fromx(e.offsetX), fromy(e.offsetY)]})
  })

  function background() {
    ctx.lineWidth = 1
    ctx.strokeStyle = ctx.fillStyle = '#666'
    ctx.beginPath()
    const r = Math.min(width, height) * 0.45
    ctx.arc(width/2, height/2, r, 0, 2*Math.PI)
    ctx.moveTo(0, height/2)
    ctx.lineTo(width, height/2)
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2, height)
    for(let i=1; i < 6; i++) {
      const phi = i * Math.PI / 6;
      const x = r * Math.cos(phi), y = r * Math.sin(phi)
      ctx.moveTo(width / 2 + x, height / 2 + y)
      ctx.lineTo(width / 2 - x, height / 2 - y)
    }
    // Arrowheads.
    const darr = 5
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width, height/2)
    ctx.lineTo(width-darr, height/2-darr)
    ctx.lineTo(width-darr, height/2+darr)
    ctx.closePath()
    ctx.fill()
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(width/2, 0)
    ctx.lineTo(width/2-darr, darr)
    ctx.lineTo(width/2+darr, darr)
    ctx.closePath()
    ctx.fill()
  }

  network.listenJson('signals', function listener(data) {
    ctx.clearRect(0, 0, width, height)
    background(0.25)
    const { target_css, css, css_alpha } = data

    if (target_css) {
      ctx.strokeStyle = '#f00'
      ctx.lineWidth = 2
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
    if (css_alpha) disp.alpha.value = css_alpha
  })
}

export const Vars = (output, {network, defs}) => {

  function dropdown(name, values) {
    const dropdown = ui.dropdown(name, {values})
    dropdown.change(value => {
      network.sender({[name]: value})
    })
    let initialized = false
    network.listenJson('signals', data => {
      if (!initialized && data.hasOwnProperty(name)) {
        dropdown.value = data[name]
        initialized = true
      }
    })
    return dropdown
  }

  h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('vars'),
    // ui.hw(
    ui.v(
      dropdown('palette', defs.palettes),
      dropdown('image', defs.images),
      'v0 v1 v2 kinect_dphi'.split(' ').map(name => ui.range(name, {network})),
    ),
  ).into(output)
}

export const ActionsButtons = (output, {name, values, network}) => {
  let value = null
  const els = h.div('cont').of(
    ui.hw(
      values.map(s => h.button(s).of(s))
    )
  ).into(output).els
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
    ActionsButtons(output, {name, values, network})
  ).into(output)
}

export const Animations = (output, {defs, network}) => {
  const els = Header('anim', h.div().of(
    ActionsButtons(output, { name: 'animation', values: defs.animations, network }),
    ui.range('anim_both', { network, name: 'both', value: 1 }),
    ui.range('anim_head', { network, name: 'head', value: 1 }),
    ui.range('anim_arms', { network, name: 'arms', value: 1 }),
    ui.h(
      ui.choice('anim_sig', { network, values: ['one', 'closest', 'rnd1', 'arousal'] }),
      '...',
      ui.toggle('anim_heart', { network, text: 'heart' }),
    ),
  )).into(output).els
}

export const Transients = (output, {network, defs}) => {

  const limit = 100
  let include = [], exclude = []
  const transients = defs.monitor_def.transients
  const disp = h.div().of(
    ui.h(
      'transients - filter:',
      h.input('include', {type: 'text'}), '\\',
      h.input('exclude', {type: 'text'}),
      h.button('reset').of('reset'),
      h.button('clear').of('clear')
    ),
    h.div('.scrollable').of(h.div('output')),
  ).into(output).els

  const matches = s => (
    !include.length || include.some(token => s.search(token) >= 0)
  ) && (
    !exclude.length || exclude.every(token => s.search(token) == -1)
  )
  function update() {
    Array.from(disp.output.children).forEach(el => 
      el.classList[matches(el.textContent) ? 'remove' : 'add']('h'))
  }
  disp.include.addEventListener('change', e => {
    include = e.target.value.split(/\s+/g).filter(x => x !== '')
    update()
  })
  disp.exclude.addEventListener('change', e => {
    exclude = e.target.value.split(/\s+/g).filter(x => x !== '')
    update()
  })
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
