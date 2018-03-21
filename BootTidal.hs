:set -XOverloadedStrings
:set prompt ""
:module Sound.Tidal.Context

(cps, nudger, getNow) <- cpsUtils'

(d1,t1) <- superDirtSetters getNow
(d2,t2) <- superDirtSetters getNow
(d3,t3) <- superDirtSetters getNow
(d4,t4) <- superDirtSetters getNow
(d5,t5) <- superDirtSetters getNow
(d6,t6) <- superDirtSetters getNow
(d7,t7) <- superDirtSetters getNow
(d8,t8) <- superDirtSetters getNow
(d9,t9) <- superDirtSetters getNow

let bps x = cps (x/2)
let hush = mapM_ ($ silence) [d1,d2,d3,d4,d5,d6,d7,d8,d9]
let solo = (>>) hush

import qualified Sound.Tidal.Scales as Scales
import Sound.Tidal.Bjorklund

-- atajos
let d = toScale (Scales.lydian)
let shh = (#gain 0)
let smoothrand ar sl = rand * ar + ( (slow sl $ sine1) + (slow (sl*(1/3)) $ tri1) )
let lfotri s vmin vmax = slow s $ scale vmin vmax tri1
let lfosin s vmin vmax = slow s $ scale vmin vmax sine1

-- e8' :: Int -> Pattern a -> Pattern a
let e8' n p = (flip const) <$> (filterValues (== True) $ listToPat $ bjorklund (n,8)) <*> p

-- e8 :: Pattern Int -> Pattern a -> Pattern a
let e8 = temporalParam e8'

-- e16' :: Int -> Pattern a -> Pattern a
let e16' n p = (flip const) <$> (filterValues (== True) $ listToPat $ bjorklund (n,16)) <*> p

-- e16 :: Pattern Int -> Pattern a -> Pattern a
let e16 = temporalParam e16'
