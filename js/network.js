
const Network = (output) => {
  const host = 'localhost'
  const signals_port = 6108
  const animation_port = 6109

  const socks = {
    animation: new WebSocket(`ws://${host}:${animation_port}`),
    signals: new WebSocket(`ws://${host}:${signals_port}`),
  }

  const disp = h.div().of(
    'animation ', h.span('animation').of('connecting'),
    ', signals ', h.span('signals').of('connecting')
  ).into(output).els;

  let animation_listeners = [], signals_listeners = []

  Object.keys(socks).forEach(key => {
    let mayberror = ''
    socks[key].addEventListener('open', function (e) {
      disp[key].textContent = 'connnected'
    })
    socks[key].addEventListener('close', function (e) {
      disp[key].textContent = mayberror + 'closed'
    })
    socks[key].addEventListener('error', function (e) {
      mayberror = 'ERROR - '
      console.log(key, 'ERROR', e)
    })
  })

  let listeners = {}
  Object.keys(socks).forEach(key => listeners[key] = [])

  socks.animation.addEventListener('message', function (e) {
    if ('size' in e.data) {
      e.data.arrayBuffer().then(function(data) {
        let view = new Uint8Array(data)
        listeners.animation.forEach(listener => listener(view))
      })
      return
    }
    console.log('unexpected data type', e.data)
    throw 'unexpected data type'
  })
  socks.signals.addEventListener('message', function (e) {
    listeners.signals.forEach(listener => listener(e.data))
  })

  function listen(key, listener) {
    listeners[key].push(listener)
    return this
  }

  function sender(d) {
    socks.signals.send(JSON.stringify(d))
  }

  return {
    listen,
    sender,
  }
}

