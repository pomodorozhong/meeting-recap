# Transcript

- Duration: 00:05:29
- Speakers: Speaker A, Speaker B, Speaker C, Speaker D
- Labels come from automatic diarization; rename or merge them in `speakers.json` and run `render`.

**[00:00:00] Speaker A:** 哈嘍,聽得到嗎?聽

**[00:00:03] Speaker B:** 得到可以,

**[00:00:04] Speaker C:** 我這邊也OK好,

**[00:00:07] Speaker A:** 那我們開始吧今天主要是看下個Sprint的Backlog然後最後再對一下Demo的實踐嗯第一個是Login Page的Bug上週QA有回報,iOS尚會閃退對,

**[00:00:24] Speaker C:** 那個我有看過應該是SDK版本太舊我這個禮拜可以先把它升級升

**[00:00:32] Speaker B:** 級會不會影響到安卓的不會

**[00:00:34] Speaker C:** 安卓的那邊是另一個package版本是分開管的OK

**[00:00:40] Speaker B:** 那

**[00:00:40] Speaker A:** 閃退是每次都會發生還是隻有某些機型

**[00:00:46] Speaker C:** 目前看起來是夠一點的iPhone比較多新的機器我自己擦不太出來了

**[00:00:55] Speaker A:** 解那可以請QA再補一下crash log啊

**[00:00:59] Speaker C:** 可以我等一下就在ticket上面留言好

**[00:01:03] Speaker A:** 那這一張就先排進來那第二個是dashboard的效能有客戶說載入要十幾秒

**[00:01:12] Speaker B:** 我覺得是API一次漏太多資料可以改成糞頁或是加一層快取對對

**[00:01:18] Speaker C:** 對而且

**[00:01:19] Speaker B:** 前端現在是一進來就把所有圖表都畫出來其實很多是使用者根本不會看的

**[00:01:26] Speaker A:** 所以你的意思是改成Lizzi loading?對,

**[00:01:28] Speaker B:** 先載入上面那三個最常用的,下面這群都在在按

**[00:01:32] Speaker C:** Mobile,本也要一起改,嗎?M

**[00:01:36] Speaker B:** obile的Dashboard只有兩張圖,應該還好,先不用

**[00:01:42] Speaker A:** 好,那這個就交給你,一共大概要幾天?

**[00:01:48] Speaker B:** API那邊,兩天,前端一天,總共三天吧包含寫Unitest沒

**[00:01:55] Speaker A:** 問題啊誒

**[00:01:57] Speaker C:** 我可以查一下嗎可以

**[00:02:00] Speaker A:** 你說就是

**[00:02:01] Speaker C:** push notification那個需求上次product teamswa這個sprint一定要做我們是不是要先討論一下範圍哦

**[00:02:11] Speaker A:** 對 差點忘了那個

**[00:02:14] Speaker B:** 需求文件我有看過 寫得蠻模糊的對

**[00:02:17] Speaker C:** 像是使用者可不可以自己關掉某一類通知上面完全沒寫嗯,

**[00:02:24] Speaker A:** 這個我下午去問PM我們先假設第一版只有開根關兩種車訂就好那

**[00:02:33] Speaker B:** 後端要準備一個settings的endpoint然後

**[00:02:37] Speaker C:** iOS跟Android的token要分開存對,

**[00:02:41] Speaker B:** 這個我來開schema哦,

**[00:02:43] Speaker A:** 那這樣估起來要多久cl

**[00:02:46] Speaker C:** ient,對,我覺得要四到五天因為兩個平臺都要做後

**[00:02:52] Speaker B:** 端大概兩天嗯

**[00:02:54] Speaker A:** 那這樣有點緊登入的bug加上通知你這個sprint會不會塞不下嗯

**[00:03:02] Speaker C:** 有一點如果SDK升級很順的話應該還可以但如果要改很多東西就不一定了還是

**[00:03:10] Speaker B:** Android那邊我先幫忙我之前有寫過一點calling真的

**[00:03:15] Speaker C:** 嗎那太好了

**[00:03:18] Speaker A:** 可以那就這樣分你先做Dashboard做完再去幫Android好那接下來是技術站的部分我們的CI最近常常跑超過20分鐘大家應該都有感覺有

**[00:03:35] Speaker C:** 超有感主

**[00:03:37] Speaker B:** 要是Integration Test每次都把整個資料庫重建一次那

**[00:03:43] Speaker A:** 有辦法改成只重建有變動的部分嗎可以

**[00:03:48] Speaker B:** 用Snapshot但要花一點時間研究我覺得這個Sprint不太可能好

**[00:03:53] Speaker A:** 那這個先開一張Ticket放在Backlog下個Sprint再看

**[00:03:59] Speaker C:** 然後Docker Image好像也很大每次Pool都很久嗯

**[00:04:07] Speaker B:** 那個可以先改成Multi Stage Beat應該半天就可以弄好半

**[00:04:13] Speaker A:** 天的話可以順便做OK

**[00:04:16] Speaker B:** 我記下來好

**[00:04:18] Speaker A:** 好,最後一件事,下週三要demo與product team,大家記得先把staging環境準備好。

**[00:04:26] Speaker C:** 下週三是幾點?

**[00:04:29] Speaker A:** 下午兩點,大概一個小時。

**[00:04:33] Speaker B:** 那staging的資料要不要先清一下?上次demo的時候有一堆測試賬號。

**[00:04:40] Speaker A:** 對,這個很重要,可以麻煩你週二之前弄好嗎?

**[00:04:45] Speaker B:** 可以。

**[00:04:46] Speaker C:** 那demo的時候通知功能應該還沒好要展示嗎可以

**[00:04:50] Speaker A:** 展示做到一半的版本但要先跟他們說清楚這不是最後的樣子

**[00:04:58] Speaker C:** 好 瞭解

**[00:05:00] Speaker A:** 那我整理一下登入的bug跟iOS的通知是你的dashboard docker image清staging還有幫忙Android是你的我去跟PM求認通知的需求這樣對嗎

**[00:05:15] Speaker B:** 對沒

**[00:05:16] Speaker C:** 錯好

**[00:05:17] Speaker A:** 還有其他問題嗎

**[00:05:19] Speaker B:** 沒有了我也

**[00:05:21] Speaker C:** 沒有好

**[00:05:23] Speaker A:** 那今天就先這樣大家辛苦了拜拜拜拜

**[00:05:27] Speaker D:** 拜拜
