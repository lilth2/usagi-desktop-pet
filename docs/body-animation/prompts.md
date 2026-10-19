# 抠图与修复提示词记录

使用内置 image_gen 进行照片抠图和必要的最小轮廓修复，透明背景开启；未使用CLI/API密钥。原图来自用户的1目录；对应原文件未覆盖。

## 第6图样例（先完成并检查）

Edit target: provided image 6, Chiikawa white round character with closed smiling eyes, pink cheeks, open happy mouth, raised small arms and original asymmetric dancing feet. Background extraction ONLY. Remove entire white/pink background, sparkle/star/flower/music-note decorations and ground shadow. Preserve EXACT original character silhouette, both original ears, head, face, body, both arms and both original feet at original pose and proportions. Do not invent new limbs, do not change facial expression or redraw style, do not add props or words. Keep all character details intact, no cropping. Output isolated full character with clean antialiased ink edges on actual fully transparent alpha background, centered with generous transparent margins. White body must remain opaque white, not transparent. This is a desktop animation source, not a redesigned character.

## 第2图

Edit ONLY source photo 2. Extract exactly its central white Chiikawa character together with the existing dark desktop monitor, monitor stand and keyboard that its hands interact with. Preserve the original ears, facial expression (open glossy eyes, pink cheeks, tiny smiling mouth), visible torso, visible hands and original proportions/drawing style. Keep original monitor and keyboard artwork. Remove pink wall, window, all plants, chair, desk surface, coffee cup, papers, mouse and unrelated scenery. Output actual transparent alpha background with clean antialiased dark ink edges and no leftover background color. Preserve white character fur as opaque white. No square white background, no fake checkerboard. Do NOT invent legs or a standing body behind the monitor/keyboard. Preserve natural occlusion by computer props. No additional limbs, no redrawn expressions, no text. Entire extracted subject and necessary computer props fully in frame with transparent margins.

## 第4图

Edit ONLY source photo 4. Extract exactly its central white Chiikawa character and the existing laptop it is using (including laptop base/keyboard), preserving original determined eyebrows, glossy eyes, cheeks, small mouth, both original ears, all visible body contour and visible hands. Preserve original laptop graphic. Remove radial blue/yellow background, chair, desk surface, left computer tower and peripheral cables/mouse. Use a real transparent alpha background, clean antialiased ink edges, opaque white fur. Do not crop ears or visible hands/laptop. Do not stretch. Do not invent the body/feet hidden behind laptop, do not make it stand, do not add limbs or change expression. Keep exact original style, proportions and pose. Full extracted subject with all laptop props visible and transparent safety margins.

## 第7图

Edit ONLY source photo 7. Extract ONLY the MIDDLE white Chiikawa character in its original rear/right-facing seated view. Keep exactly the rounded ears, visible right-facing eye/profile and cheek, original back/body silhouette and small round tail. Do not rotate to front, do not redesign or change its purple/white night lighting or original painted line style. Remove ALL landscape, grass, sky, blue character on left and yellow rabbit character on right, and all unrelated characters/props. Real fully transparent alpha background. Preserve white fur as opaque, clean antialiased contour without dark landscape fringe. Restore only the minimal smooth bottom contour interrupted by a few grass blades, without adding unseen feet or inventing new anatomy. This minimal lower-contour restoration will be explicitly documented separately. Keep full silhouette, both ears and tail inside generous transparent margins. No text or new decorations.

## 第2图下缘修复（单独保存结果，只合成限定区域）

Precisely edit this transparent Chiikawa-with-desktop-computer cutout. Keep the monitor, stand, keyboard, complete ears/head, exact glossy eyes/pink cheeks/smile, both visible hands, original pose, style and proportions unchanged. Repair ONLY the unfinished exposed lower-right body edge where the original removed desk left a flat white cut-off/fringe: close that exposed torso edge with one gentle rounded ink contour consistent with the existing brown outline, curving naturally behind the keyboard. This is a MINIMAL OCCLUSION REPAIR, not a new standing body. Do not add any feet, legs, limbs or props. No changes to face or computer. Remove any detached white fringe below that edge. Preserve genuine transparent alpha background and opaque white fur. Full subject remains uncropped, no scenery, no shadows.

## 本地后处理

连通域清除游离噪点，实体Alpha恢复为255，第7图去掉生成的外侧半透明泛光；保留抗锯齿边缘。透明源图、统一比例注册、预乘Alpha采样、控制点和身体动作图集均由仓库脚本生成，不通过图像模型生成不存在的步行动作。补绘区域与原始抠图分别保存。
