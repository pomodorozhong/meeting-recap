# Transcript (script-relabeled)

**[00:00:00] Speaker C:** 哈囉，聽得到嗎？

**[00:00:03] Speaker A:** 聽得到。

**[00:00:04] Speaker B:** 可以，我這邊也 OK。

**[00:00:06] Speaker C:** 好，那我們開始吧。今天主要是看下個 sprint 的 backlog，然後最後再對一下 demo 的時間。

**[00:00:15] Speaker A:** 嗯。

**[00:00:16] Speaker C:** 第一個是 login page 的 bug，上週 QA 有回報，iOS 上會閃退。

**[00:00:23] Speaker B:** 對，那個我有看過，應該是 SDK 版本太舊。我這個禮拜可以先把它升級。

**[00:00:32] Speaker A:** 升級會不會影響到 Android？

**[00:00:34] Speaker B:** 不會，Android 那邊是另一個 package，版本是分開管的。

**[00:00:39] Speaker A:** OK。

**[00:00:40] Speaker C:** 那閃退是每次都會發生，還是只有某些機型？

**[00:00:46] Speaker B:** 目前看起來是舊一點的 iPhone 比較多，新的機器我自己測不太出來。

**[00:00:55] Speaker C:** 了解。那可以請 QA 再補一下 crash log 嗎？

**[00:00:59] Speaker B:** 可以，我等一下就在 ticket 上面留言。

**[00:01:03] Speaker C:** 好，那這張就先排進來。

**[00:01:07] Speaker C:** 那第二個是 dashboard 的效能。有客戶說載入要十幾秒。

**[00:01:12] Speaker A:** 我覺得是 API 一次撈太多資料，可以改成分頁，或是加一層快取。

**[00:01:17] Speaker B:** 對對對。

**[00:01:18] Speaker A:** 而且前端現在是一進來就把所有圖表都畫出來，其實很多是使用者根本不會看的。

**[00:01:26] Speaker C:** 所以你的意思是改成 lazy loading？

**[00:01:28] Speaker A:** 對，先載入上面那三個最常用的，下面的捲到再載。

**[00:01:32] Speaker B:** 那 mobile 版也要一起改嗎？

**[00:01:35] Speaker A:** mobile 的 dashboard 只有兩張圖，應該還好，先不用。

**[00:01:41] Speaker C:** 好，那這個就交給你，預估大概要幾天？

**[00:01:48] Speaker A:** API 那邊兩天，前端一天，總共三天吧，包含寫 unit test。

**[00:01:55] Speaker C:** 沒問題。

**[00:01:57] Speaker B:** 欸，我可以插一下嗎？

**[00:01:59] Speaker C:** 可以，你說。

**[00:02:01] Speaker B:** 就是 push notification 那個需求，上次 product team 說這個 sprint 一定要做，我們是不是要先討論一下範圍？

**[00:02:11] Speaker C:** 喔對，差點忘了。

**[00:02:14] Speaker A:** 那個需求文件我有看過，寫得滿模糊的。

**[00:02:17] Speaker B:** 對，像是使用者可不可以自己關掉某一類通知，上面完全沒寫。

**[00:02:24] Speaker C:** 嗯，這個我下午去問 PM。我們先假設第一版只有開跟關兩種設定就好。

**[00:02:33] Speaker A:** 那後端要準備一個 settings 的 endpoint。

**[00:02:36] Speaker B:** 然後 iOS 跟 Android 的 token 要分開存。

**[00:02:40] Speaker A:** 對，這個我來開 schema。

**[00:02:42] Speaker C:** 好，那這樣估起來要多久？

**[00:02:46] Speaker B:** client 端我覺得要四到五天，因為兩個平台都要做。

**[00:02:52] Speaker A:** 後端大概兩天。

**[00:02:54] Speaker C:** 嗯，那這樣有點緊。登入的 bug 加上通知，你這個 sprint 會不會塞不下？

**[00:03:01] Speaker B:** 嗯，有一點。如果 SDK 升級很順的話應該還可以，但如果要改很多東西就不一定了。

**[00:03:10] Speaker A:** 還是 Android 那邊我先幫忙？我之前有寫過一點 Kotlin。

**[00:03:15] Speaker B:** 真的嗎？那太好了。

**[00:03:18] Speaker C:** 可以，那就這樣分。你先做 dashboard，做完再去幫 Android。

**[00:03:24] Speaker A:** 好。

**[00:03:25] Speaker C:** 那接下來是技術債的部分。我們的 CI 最近常常跑超過二十分鐘，大家應該都有感覺。

**[00:03:34] Speaker B:** 有，超有感。

**[00:03:37] Speaker A:** 主要是 integration test 每次都把整個資料庫重建一次。

**[00:03:42] Speaker C:** 那有辦法改成只重建有變動的部分嗎？

**[00:03:48] Speaker A:** 可以用 snapshot，但要花一點時間研究，我覺得這個 sprint 不太可能。

**[00:03:53] Speaker C:** 好，那這個先開一張 ticket 放在 backlog，下個 sprint 再看。

**[00:03:59] Speaker B:** 然後 Docker image 好像也很大，每次 pull 都很久。

**[00:04:06] Speaker A:** 嗯，那個可以先改成 multi-stage build，應該半天就可以弄好。

**[00:04:12] Speaker C:** 半天的話可以順便做。

**[00:04:15] Speaker A:** OK，我記下來。

**[00:04:17] Speaker C:** 好，最後一件事，下週三要 demo 給 product team，大家記得先把 staging 環境準備好。

**[00:04:26] Speaker B:** 下週三是幾點？

**[00:04:28] Speaker C:** 下午兩點，大概一個小時。

**[00:04:34] Speaker A:** 那 staging 的資料要不要先清一下？上次 demo 的時候有一堆測試帳號。

**[00:04:40] Speaker C:** 對，這個很重要。可以麻煩你週二之前弄好嗎？

**[00:04:45] Speaker A:** 可以。

**[00:04:46] Speaker B:** 那 demo 的時候通知功能應該還沒好，要展示嗎？

**[00:04:50] Speaker C:** 可以展示做到一半的版本，但要先跟他們說清楚這不是最後的樣子。

**[00:04:58] Speaker B:** 好，了解。

**[00:05:00] Speaker C:** 那我整理一下。登入的 bug 跟 iOS 的通知是你的；dashboard、Docker image、清 staging，還有幫忙 Android 是你的；我去跟 PM 確認通知的需求。這樣對嗎？

**[00:05:15] Speaker A:** 對。

**[00:05:16] Speaker B:** 沒錯。

**[00:05:17] Speaker C:** 好，還有其他問題嗎？

**[00:05:20] Speaker A:** 沒有了。

**[00:05:21] Speaker B:** 我也沒有。

**[00:05:22] Speaker C:** 好，那今天就先這樣，大家辛苦了，拜拜。

**[00:05:27] Speaker B:** 拜拜。

**[00:05:28] Speaker A:** 拜拜。
