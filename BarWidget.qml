import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons
import qs.Commons as Commons

Panel {
  id: root
  moduleName: "ciro.youtube-music"
  ipcTarget: "ciro.youtube-music"
  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }
  property var snapshot: ({})
  property double now: Date.now()/1000
  property int section: 0
  property bool pendingSearch: false
  property string processError: ""
  property var queuedCommands: []
  readonly property string base: decodeURIComponent(Qt.resolvedUrl(".").toString().replace(/^(?:file:\/\/|qs:)/,""))
  readonly property bool connected: !!snapshot.connected && now-Number(snapshot.updated || 0)<8
  readonly property var player: snapshot.player || ({})
  function transport(action) { send({action:action}) }
  readonly property var entries: section === 2 ? (snapshot.results || []) : (snapshot.recent || [])
  readonly property int effectiveBarSize: bar ? bar.barSize : Style.bar.sizeHorizontal
  implicitWidth: button.implicitWidth
  implicitHeight: effectiveBarSize
  function send(value) {
    queuedCommands=queuedCommands.concat([JSON.stringify(value)])
    flush()
  }
  function flush() {
    if(command.running || !queuedCommands.length)return
    command.command=["python3",base+"backend/music.py","request",queuedCommands[0]]
    queuedCommands=queuedCommands.slice(1)
    command.running=true
  }
  function readState() {
    now=Date.now()/1000
    stateFile.reload()
  }
  Component.onCompleted: send({action:"ensure"})
  function formatTime(v) { v=Number(v)||0; return Math.floor(v/60)+":"+String(Math.floor(v%60)).padStart(2,"0") }
  FileView {
    id: stateFile
    path: Quickshell.env("HOME")+"/.local/state/omarchy/music-public/state.json"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: { try { root.snapshot=JSON.parse(text()); root.pendingSearch=!!root.snapshot.busy } catch(e) {} }
  }
  Timer { interval: 1500; running: true; repeat: true; onTriggered: root.readState() }
  Process {
    id: command
    stderr: StdioCollector { id: processStderr }
    onExited: function(exitCode) {
      root.processError=exitCode===0 ? "" : (processStderr.text || strings.t("serviceError"))
      Qt.callLater(root.flush)
    }
  }
  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    labelVisible: false
    hasVisualContent: true
    fixedWidth: Style.bar.iconSlot
    tooltipText: "YouTube Music"
    onPressed: root.toggle()
    Image {
      anchors.centerIn: parent
      source: Qt.resolvedUrl("youtube-music.svg")
      width: Style.bar.iconSize; height: width
      sourceSize.width: width*2; sourceSize.height: height*2
      scale: button.pressScale
      opacity: root.connected ? 1 : 0.75
    }
  }
  KeyboardPanel {
    id: popup
    anchorItem: button; bar: root.bar; owner: root
    open: root.opened
    focusTarget: search
    contentWidth: fittedContentWidth(Style.space(410))
    contentHeight: fittedContentHeight(column.implicitHeight)
    Column {
      id: column
      anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
      spacing: Style.space(14)
      Row {
        width: parent.width
        Text { text: "YouTube Music"; textFormat: Text.PlainText; color: Commons.Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.subtitle; font.bold: true; width: parent.width-refresh.width }
        Button { id: refresh; iconText: "󰓛"; tooltipText: strings.t("stop"); enabled: root.connected; onClicked: root.send({action:"stop"}) }
      }
      Text {
        width: parent.width
        visible: !root.connected
        textFormat: Text.PlainText
        text: strings.t("connectHint")
        color: Commons.Color.foreground
        font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
        wrapMode: Text.WordWrap
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        TextField {
          id: search
          width: parent.width-searchButton.width-parent.spacing
          placeholderText: strings.t("search")
          enabled: root.connected
          onAccepted: searchButton.clicked()
        }
        Button {
          id: searchButton
          iconText: "󰍉"; tooltipText: strings.t("search")
          enabled: root.connected && search.text.trim().length>0 && !root.snapshot.busy
          onClicked: { root.section=2; root.pendingSearch=true; root.send({action:"search",query:search.text.trim()}) }
        }
      }
      Row {
        spacing: Style.space(8)
        Button { text: strings.t("recent"); selected: root.section===0; onClicked: root.section=0 }
        Button { text: strings.t("results"); selected: root.section===2; onClicked: root.section=2 }
      }
      Text {
        width: parent.width
        visible: !!root.processError || !!root.snapshot.error || !!root.snapshot.busy || !!root.snapshot.loading
        text: root.processError || root.snapshot.error || (root.snapshot.loading ? strings.t("loadingTrack") : strings.t("loading"))
        textFormat: Text.PlainText; wrapMode: Text.WordWrap
        color: Commons.Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
      }
      ListView {
        id: list
        width: parent.width
        height: Style.space(250)
        clip: true
        spacing: Style.space(6)
        model: root.connected ? root.entries : []
        boundsBehavior: Flickable.StopAtBounds
        delegate: Rectangle {
          required property var modelData
          width: ListView.view.width; height: Style.space(58)
          radius: Style.cornerRadius
          color: mouse.containsMouse ? Style.selectedFillFor(Commons.Color.foreground,Commons.Color.accent) : "transparent"
          Row {
            anchors.fill: parent; anchors.margins: Style.space(5); spacing: Style.space(10)
            Rectangle {
              width: Style.space(48); height: width
              color: Style.normalFillFor(Commons.Color.foreground,Commons.Color.accent)
              radius: Style.cornerRadius
              SizedImage { anchors.fill: parent; url: modelData.art || ""; crop: true }
              Text { anchors.centerIn: parent; visible: !modelData.art; text: "󰝚"; textFormat: Text.PlainText; color: Commons.Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.icon }
            }
            Column {
              width: parent.width-Style.space(58); anchors.verticalCenter: parent.verticalCenter; spacing: Style.space(4)
              Text { width: parent.width; text: modelData.title; textFormat: Text.PlainText; elide: Text.ElideRight; color: Commons.Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true }
              Text { width: parent.width; text: modelData.subtitle; textFormat: Text.PlainText; elide: Text.ElideRight; color: Commons.Color.foreground; opacity: 0.7; font.family: Style.font.family; font.pixelSize: Style.font.caption }
            }
          }
          MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.send({action:"play",kind:modelData.kind,id:modelData.id}) }
        }
        Text {
          anchors.centerIn: parent; width: parent.width-Style.space(32)
          visible: list.count===0
          text: !root.connected ? strings.t("waiting") : root.snapshot.busy ? strings.t("loading") : root.section===0 ? strings.t("noRecent") : root.section===2 ? strings.t("noResults") : strings.t("noLibrary")
          textFormat: Text.PlainText; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
          color: Commons.Color.foreground; opacity: 0.7; font.family: Style.font.family; font.pixelSize: Style.font.bodySmall
        }
      }
      PanelSeparator { foreground: Commons.Color.foreground }
      Row {
        width: parent.width; spacing: Style.space(12)
        Rectangle {
          width: Style.space(54); height: width; radius: Style.cornerRadius
          color: Style.normalFillFor(Commons.Color.foreground,Commons.Color.accent)
          SizedImage { anchors.fill: parent; crop: true; url: root.player.art || "" }
          Text { anchors.centerIn: parent; visible: !root.player.art; text: "󰝚"; textFormat: Text.PlainText; color: Commons.Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.icon }
        }
        Column {
          width: parent.width-Style.space(66); anchors.verticalCenter: parent.verticalCenter; spacing: Style.space(5)
          Text { width: parent.width; text: root.player.title || strings.t("nothingPlaying"); textFormat: Text.PlainText; elide: Text.ElideRight; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true; color: Commons.Color.foreground }
          Text { width: parent.width; text: root.player.artist || ""; textFormat: Text.PlainText; elide: Text.ElideRight; font.family: Style.font.family; font.pixelSize: Style.font.caption; color: Commons.Color.foreground; opacity: 0.7 }
        }
      }
      Rectangle {
        width: parent.width; height: Style.space(3)
        color: Style.normalFillFor(Commons.Color.foreground,Commons.Color.accent)
        Rectangle { height: parent.height; width: parent.width*Math.min(1,Number(root.player.position||0)/Math.max(1,Number(root.player.duration||1))); color: Commons.Color.foreground }
      }
      Row {
        width: parent.width; spacing: Style.space(8)
        Text { width: (parent.width-transport.width-parent.spacing*2)/2; anchors.verticalCenter: parent.verticalCenter; text: root.formatTime(root.player.position); textFormat: Text.PlainText; font.family: Style.font.family; font.pixelSize: Style.font.caption; color: Commons.Color.foreground }
        Row {
          id: transport; spacing: Style.space(8)
          Button { iconText: "󰒮"; tooltipText: strings.t("previous"); enabled: root.connected && !!root.player.title; onClicked: root.transport("previous") }
          Button { iconText: root.player.playing ? "󰏤" : "󰐊"; tooltipText: strings.t("playPause"); enabled: root.connected && !!root.player.title; onClicked: root.transport("toggle") }
          Button { iconText: "󰒭"; tooltipText: strings.t("next"); enabled: root.connected && !!root.player.title; onClicked: root.transport("next") }
        }
        Text { width: (parent.width-transport.width-parent.spacing*2)/2; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignRight; text: root.formatTime(root.player.duration); textFormat: Text.PlainText; font.family: Style.font.family; font.pixelSize: Style.font.caption; color: Commons.Color.foreground }
      }
    }
  }
}
