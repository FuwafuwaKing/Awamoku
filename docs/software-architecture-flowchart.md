# あわもく ソフトウェア構成フローチャート

この図は、実行時にデータがどこから来て、どのノードが判断し、何を表示・走行へ渡すかを示す。ノード名・通信名は追跡用の補助情報であり、主表記は役割と受け渡す内容である。

```mermaid
flowchart TB
    classDef input fill:#DBEAFE,stroke:#1D4ED8,color:#172554,stroke-width:2px
    classDef core fill:#DCFCE7,stroke:#15803D,color:#052E16,stroke-width:2px
    classDef safety fill:#FEF3C7,stroke:#B45309,color:#451A03,stroke-width:3px
    classDef robot fill:#F3E8FF,stroke:#7E22CE,color:#3B0764,stroke-width:2px
    classDef output fill:#FCE7F3,stroke:#BE185D,color:#500724,stroke-width:2px

    subgraph INPUT[入力: 参加者と Unity]
        direction LR
        P[参加者<br/>赤チーム・白チーム]:::input
        U[Unity 操作画面<br/>疑似声量、開始、停止、リセット、非常停止を入力]:::input
        IN[Unity と ROS 2 の通信窓口<br/>TCP 10000番で操作・声量を ROS 2 へ渡す<br/>UnityEndpoint]:::input
        V[声量入力の選択・整形<br/>疑似入力か実マイク入力を選び、0〜1へ制限<br/>古い入力は 0 として扱う<br/>voice_source_mux]:::core
        P -->|呼びかけを操作へ反映| U
        U -->|赤・白の疑似声量、ゲーム操作| IN
        IN -->|ROS 2 へ届いた疑似声量と操作| V
    end

    subgraph CONTROL[ゲーム判断と走行制御]
        direction LR
        G[ゲーム状態管理<br/>声量・操作・現在地から、雲の状態、目標、得点、安心度、残り時間、演出を決定<br/>cloud_game_manager]:::core
        M[移動方針の計算<br/>周回、接近、落ち着いた側の周回、中央への帰還の希望速度を作る<br/>cloud_motion_controller]:::core
        S[安全監視・最終走行命令<br/>障害物、境界、入力途絶、非常停止を確認<br/>唯一、車輪速度を送れる<br/>safety_guard]:::safety
        R[Gazebo 上の TurtleBot3<br/>最終速度で走行し、位置・姿勢・前方障害物を計測<br/>gzserver]:::robot
        G -->|雲の状態、目標チーム、ゲーム進行| M
        M -->|安全確認前の希望速度<br/>前進量・回転量| S
        S -->|安全確認済みの最終速度<br/>前進量・回転量| R
    end
    V -->|有効な赤・白の声量| G

    subgraph OUTPUT[観測の戻りと Unity 表示・演出]
        direction LR
        O[観測の戻りと Unity 用情報<br/>位置・姿勢: ゲーム判定・移動方針が次周期に読む<br/>前方障害物・位置: 安全監視が次周期に読む<br/>表示用: 状態、得点、安心度、時間、位置、希望速度、安全後速度、演出]:::output
        OUT[Unity と ROS 2 の通信窓口<br/>同じ TCP 接続で結果を Unity へ渡す<br/>UnityEndpoint]:::output
        D[Unity ダッシュボード・雲モデル<br/>状態、得点、残り時間、位置、速度を表示<br/>位置姿勢に合わせて雲を動かす]:::output
        X[演出出力<br/>Unity: 落ち着かせたチームの方向へ雲から泡を噴射<br/>CloudEffectPlayer<br/>物理装置: LED・送風・泡装置向けの指示を受ける。現状はログ出力のみ<br/>effect_adapter]:::output
        O -->|画面表示用の位置・速度・ゲーム結果| OUT
        OUT -->|Unity に届く表示情報| D
        O -->|演出イベント、演出モード、目標チーム| X
    end
    R -->|位置・姿勢、前方障害物までの距離| O
    G -->|状態、得点、安心度、残り時間、演出イベント| O
    M -->|画面表示用の希望速度| O
    S -->|画面表示用の安全後速度| O
```

## 技術名と渡す情報の対応

| 役割 | ノード / 実装名 | 渡す情報 |
| --- | --- | --- |
| Unity と ROS 2 の橋渡し | `UnityEndpoint` | Unity の声量・操作を ROS 2 へ渡し、ROS 2 の状態・位置・速度・演出を Unity へ渡す。 |
| 声量の選択 | `voice_source_mux` | 疑似声量または実マイク声量を選び、赤・白それぞれの有効な声量を出す。 |
| ルールと得点 | `cloud_game_manager` | 雲の状態、目標チーム、赤白の得点と安心度、残り時間、演出モード・イベントを出す。 |
| 移動方針 | `cloud_motion_controller` | 状態と位置から、安全確認前の前進速度・角速度を出す。 |
| 安全の最終判断 | `safety_guard` | 障害物、境界、タイムアウト、非常停止を確認した最終速度だけを出す。 |
| シミュレーションロボット | `TurtleBot3 / Gazebo` | 位置・姿勢、前方の距離計測を返し、最終速度で走行する。 |
| Unity の画面・雲・泡 | `AwamokuDashboard` ほか | ROS 2 の結果を表示し、位置追従と方向付きバブルを再現する。 |
