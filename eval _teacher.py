import time
import random
import base64
import requests
import jwt
import io
from PIL import Image, ImageEnhance
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

def debug_page_structure(driver):
    """调试页面结构 - 分析表单元素"""
    print("\n🔍 === 调试页面结构 ===")
    
    try:
        # 分析表格结构
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"📊 找到 {len(tables)} 个表格")
        
        # 分析单选按钮
        all_radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        print(f"🔘 找到 {len(all_radios)} 个单选按钮")
        
        # 分析表格行
        table_rows = driver.find_elements(By.XPATH, "//tr[td//input[@type='radio']]")
        print(f"📋 找到 {len(table_rows)} 个包含单选按钮的表格行")
        
        # 分析按名称分组的单选按钮
        radio_names = set()
        for radio in all_radios:
            name = radio.get_attribute('name')
            if name:
                radio_names.add(name)
        print(f"🏷️ 单选按钮组数量: {len(radio_names)}")
        
        # 分析文本域
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        print(f"📝 找到 {len(textareas)} 个文本域")
        
        # 分析提交按钮
        submit_buttons = []
        for selector in ["//button[contains(text(), '保存')]", "//input[@value='保存']", 
                        "//button[contains(text(), '提交')]", "//input[@value='提交']",
                        "//input[@type='submit']", "//button[@type='submit']"]:
            buttons = driver.find_elements(By.XPATH, selector)
            submit_buttons.extend(buttons)
        print(f"💾 找到 {len(submit_buttons)} 个可能的提交按钮")
        
        # 显示每行单选按钮的详细信息
        print("\n📋 各行单选按钮详情:")
        for i, row in enumerate(table_rows[:3]):  # 只显示前3行
            try:
                row_radios = row.find_elements(By.XPATH, ".//input[@type='radio']")
                row_text = row.find_element(By.XPATH, "./td[1]").text.strip()[:20]
                print(f"  第{i+1}行 '{row_text}': {len(row_radios)}个选项")
                
                # 显示各选项的位置和值
                radios_with_pos = []
                for j, radio in enumerate(row_radios):
                    rect = radio.rect
                    value = radio.get_attribute('value') or f'选项{j+1}'
                    radios_with_pos.append((value, rect['x'], j))
                
                # 按位置排序显示
                radios_with_pos.sort(key=lambda x: x[1])
                position_info = " → ".join([f"{info[0]}(位置{info[1]:.0f})" for info in radios_with_pos])
                print(f"    选项位置: {position_info}")
                
            except Exception as e:
                print(f"  第{i+1}行: 解析失败 - {e}")
        
        print("🆗 调试完成\n")
        
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")

def quick_evaluation():
    """快速评估 - 采用循环模式，一次评估一个URL"""
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    
    try:
        print("\n" + "="*50)
        print("🤖 智谱AI (GLM-4V) 验证码识别配置 (可选)")
        zhipu_api_key = input("请输入智谱AI API密钥（直接回车跳过，将手动处理验证码）: ").strip()
        if zhipu_api_key:
            print("✅ 智谱AI API已配置。")
        else:
            print("ℹ️ 未配置智谱AI API，将需要手动输入验证码。")
        print("="*50)

        # 首先登录
        print("🌐 导航到登录页面...")
        login_url = "https://sep.ucas.ac.cn/appStoreStudent"
        driver.get(login_url)
        
        print("请完成登录:")
        print("1. 输入用户名和密码")
        print("2. 输入验证码")
        print("3. 点击登录")
        input("登录完成后按回车继续...")
        
        success_count = 0
        total_count = 0
        first_run = True

        while True:
            print("\n" + "="*50)
            print("请输入下一个评估页面的URL (直接按回车退出流程):")
            print("示例: https://xkcts.ucas.ac.cn:8443/evaluate/evaluateTeacher/78810/278488/1541/0")
            eval_url = input("URL: ").strip()

            if not eval_url:
                print("🏁 用户选择退出。")
                break
            
            total_count += 1
            print(f"\n📝 开始评估第 {total_count} 个课程...")
            print(f"URL: {eval_url}")
            
            try:
                # 导航到评估页面
                driver.get(eval_url)
                
                # 检查是否需要重新登录 (使用更健壮的等待方式)
                try:
                    WebDriverWait(driver, 3).until(
                        lambda d: "登录" in d.page_source or "login" in d.current_url.lower()
                    )
                    print("⚠️ 会话可能已失效，请重新登录")
                    input("登录完成后按回车继续...")
                    driver.get(eval_url)
                except TimeoutException:
                    pass # 很好，不需要重新登录

                # 显式等待，确保页面主要内容加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//body"))
                )
                
                # 检查是否在正确的评估页面
                if "evaluate" not in driver.current_url and "评估" not in driver.page_source:
                    print("❌ 当前似乎不是评估页面，请检查URL或登录状态。")
                    print(f"   当前URL: {driver.current_url}")
                    continue
                
                # 调试页面结构（仅在第一次评估时运行）
                if first_run:
                    debug_page_structure(driver)
                    first_run = False
                
                # 填写评估表单
                if fill_evaluation_form(driver, zhipu_api_key=zhipu_api_key):
                    success_count += 1
                    print(f"✅ 第 {total_count} 个课程评估成功！")
                else:
                    print(f"❌ 第 {total_count} 个课程评估失败或未完整保存。")
                
            except Exception as e:
                print(f"💥 评估第 {total_count} 个课程时发生严重错误: {e}")
                continue
        
        print("\n" + "="*50)
        print(f"🎉 评估流程结束！")
        print(f"共尝试评估 {total_count} 个课程，成功 {success_count} 个。")
        return True
        
    except Exception as e:
        print(f"💥 脚本发生意外错误: {e}")
        return False
    
    finally:
        print("所有操作已完成。")
        input("按回车关闭浏览器...")
        driver.quit()

def generate_zhipu_token(apikey: str):
    """根据智谱API Key生成认证用的JWT Token"""
    try:
        id, secret = apikey.split(".")
    except Exception as e:
        raise Exception("无效的智谱API Key格式，应为 'id.secret'", e)

    payload = {
        "api_key": id,
        "exp": int(round(time.time() * 1000)) + 60 * 1000,  # 60秒有效期
        "timestamp": int(round(time.time() * 1000)),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )

def solve_captcha_with_zhipu_llm(api_key, image_base64):
    """
    使用智谱AI GLM-4V模型识别验证码。
    """
    print("🤖 正在调用智谱AI (GLM-4V) API识别验证码...")
    
    try:
        token = generate_zhipu_token(api_key)
    except Exception as e:
        print(f"❌ 生成智谱Token失败: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    api_endpoint = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    payload = {
        "model": "glm-4v",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "图片里的验证码是什么？请只返回验证码的文本内容，不要包含任何其他说明和解释。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 20
    }

    try:
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content'].strip()
        print(f"🤖 大模型原始返回: '{content}'")
        
        # 改进的验证码提取逻辑
        import re
        
        # 尝试多种模式提取验证码
        patterns = [
            r'[a-zA-Z0-9]{3,6}$',  # 行末的3-6位字母数字组合
            r'是([a-zA-Z0-9]{3,6})',  # "是"后面的验证码
            r'码是([a-zA-Z0-9]{3,6})',  # "码是"后面的验证码
            r'([a-zA-Z0-9]{3,6})',  # 任何3-6位字母数字组合
        ]
        
        captcha_text = None
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                if pattern.startswith('[a-zA-Z0-9]') and pattern.endswith('$'):
                    captcha_text = match.group(0)
                else:
                    captcha_text = match.group(1)
                break
        
        # 如果正则没匹配到，尝试简单的字母数字过滤
        if not captcha_text:
            alnum_only = ''.join(filter(str.isalnum, content))
            if 3 <= len(alnum_only) <= 6:
                captcha_text = alnum_only
        
        if captcha_text:
            print(f"🎯 提取的验证码: '{captcha_text}'")
            return captcha_text
        else:
            print("⚠️ 无法从返回内容中提取验证码")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ 调用智谱API时网络错误: {e}")
    except (KeyError, IndexError) as e:
        print(f"❌ 解析API响应失败，格式可能不正确: {e}")
        print(f"   收到的响应: {response.text}")
    except Exception as e:
        print(f"❌ 调用智谱API时发生未知错误: {e}")
    
    return None

def click_radio_button(driver, radio_element, row_num):
    """
    使用多种方法尝试点击一个单选按钮，以提高成功率。
    返回 True 如果成功，否则返回 False。
    """
    try:
        # 等待元素变得可点击，这是最关键的一步
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(radio_element))

        # 策略一：使用ActionChains，最接近真实用户操作
        try:
            ActionChains(driver).move_to_element(radio_element).click().perform()
            time.sleep(0.1)
            if radio_element.is_selected():
                print(f"✅ 第 {row_num} 行 - ActionChains 点击成功")
                return True
        except Exception:
            pass  # 失败则尝试下一种方法

        # 策略二：使用JavaScript直接点击
        try:
            driver.execute_script("arguments[0].click();", radio_element)
            time.sleep(0.1)
            if radio_element.is_selected():
                print(f"✅ 第 {row_num} 行 - JavaScript 点击成功")
                return True
        except Exception:
            pass  # 失败则尝试下一种方法
            
        # 策略三：强制设置checked状态并触发事件
        try:
            driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change'));", radio_element)
            time.sleep(0.1)
            if radio_element.is_selected():
                print(f"✅ 第 {row_num} 行 - 强制设置成功")
                return True
        except Exception:
            pass

        print(f"❌ 第 {row_num} 行所有点击方法均失败")
        return False

    except TimeoutException:
        print(f"❌ 第 {row_num} 行 - 等待按钮可点击超时")
        # 输出详细的调试信息
        is_disp = radio_element.is_displayed()
        is_enabled = radio_element.is_enabled()
        size = radio_element.size
        location = radio_element.location
        print(f"  > 调试信息: 可见={is_disp}, 可用={is_enabled}, 尺寸={size}, 位置={location}")
        return False
    except Exception as e:
        print(f"❌ 第 {row_num} 行 - 点击时发生未知错误: {e}")
        return False

def fill_evaluation_form(driver, zhipu_api_key=None):
    """填写评估表单（重构版）"""
    try:
        wait = WebDriverWait(driver, 10)
        print("📝 开始填写评估表单...")
        
        print("🧠 使用新的高可靠性策略填写单选按钮...")
        try:
            # 1. 等待评估行完全加载
            table_rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//tr[td//input[@type='radio']]")))
            print(f"📋 找到 {len(table_rows)} 个包含单选按钮的评估行")
            
            filled_count = 0
            total_rows = len(table_rows)

            for i, row in enumerate(table_rows):
                row_num = i + 1
                try:
                    # 2. 在行内查找所有选项
                    radios_in_row = row.find_elements(By.XPATH, ".//input[@type='radio']")
                    if not radios_in_row:
                        print(f"⚠️ 第 {row_num} 行未找到选项")
                        continue

                    # 3. 按水平位置排序，找出最左边的选项
                    radios_with_pos = sorted([(r, r.location['x']) for r in radios_in_row], key=lambda x: x[1])
                    best_radio = radios_with_pos[0][0]
                    
                    if best_radio.is_selected():
                        print(f"ℹ️ 第 {row_num} 行已选择，跳过")
                        filled_count += 1
                        continue
                    
                    # 4. 滚动到该选项，确保它在可视范围内
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", best_radio)
                    time.sleep(0.3) # 滚动后短暂暂停

                    # 5. 使用新的高可靠性点击函数
                    if click_radio_button(driver, best_radio, row_num):
                        filled_count += 1
                    else:
                        # 终极调试：如果所有方法都失败，保存截图
                        filename = f"eval_fail_row_{row_num}.png"
                        driver.save_screenshot(filename)
                        print(f"📸 关键失败：已保存截图至 {filename} 供分析。")

                except Exception as e:
                    print(f"❌ 处理第 {row_num} 行时发生意外错误: {e}")
                    continue
            
            print(f"✅ 完成单选题填写，成功填写 {filled_count}/{total_rows} 行")
            if filled_count < total_rows:
                print("⚠️ 部分单选题未能自动完成，请检查失败截图或手动完成。")
                input("手动完成后按回车继续...")

        except TimeoutException:
            print("❌ 未能找到评估表格，跳过单选题。")
        except Exception as e:
            print(f"❌ 处理单选题时发生严重错误: {e}")
        
        time.sleep(1)
        
        # 处理文本域
        try:
            textareas = driver.find_elements(By.TAG_NAME, "textarea")
            print(f"🔍 找到 {len(textareas)} 个文本域")
            
            if textareas:
                comments = [
                    "老师教学认真负责，课程内容丰富，讲解清晰老师治学严谨，教学内容充实。aaaa。",
                    "老师专业水平高，备课充分，课程质量很高。老师治学严谨，教学内容充实。aaaa",
                    "课程安排合理，老师耐心解答问题。老师治学严谨，教学内容充实。aaaa",
                    "教学态度认真，课堂氛围活跃。老师治学严谨，教学内容充实。aaaa",
                    "老师治学严谨，教学内容充实。aaaa"
                ]
                
                for i, textarea in enumerate(textareas):
                    try:
                        if textarea.is_displayed() and textarea.is_enabled():
                            comment = random.choice(comments)
                            textarea.clear()
                            textarea.send_keys(comment)
                            print(f"✅ 填写了第 {i+1} 个文本域")
                    except Exception as e:
                        print(f"❌ 填写第 {i+1} 个文本域失败: {e}")
            else:
                print("ℹ️ 未找到文本域")
                
        except Exception as e:
            print(f"❌ 处理文本域时出错: {e}")
        
        # 处理验证码
        captcha_solved = False
        try:
            # 定位验证码元素
            captcha_input, captcha_image = find_captcha_elements(driver)
            
            if captcha_input and captcha_image and zhipu_api_key:
                MAX_ATTEMPTS = 3
                for attempt in range(MAX_ATTEMPTS):
                    print(f"\n🤖 ===== 验证码识别: 第 {attempt + 1}/{MAX_ATTEMPTS} 次 =====")
                    
                    # 获取验证码解决方案
                    captcha_solution = get_captcha_solution(driver, captcha_image, zhipu_api_key)

                    if not captcha_solution:
                        print("⚠️ 验证码识别失败，刷新后重试...")
                        try:
                            captcha_image.click()
                            time.sleep(1)
                        except Exception as e:
                            print(f"❌ 刷新验证码失败: {e}")
                        continue

                    # 填写验证码
                    print(f"✍️ 正在填入验证码: '{captcha_solution}'")
                    try:
                        driver.execute_script("arguments[0].value = arguments[1];", captcha_input, captcha_solution)
                        time.sleep(0.5)
                        
                        # 验证填写结果
                        filled_value = captcha_input.get_attribute('value')
                        print(f"🕵️ 验证填写结果: '{filled_value}'")

                        if filled_value != captcha_solution:
                            print("❌ 填写失败或被清空，刷新重试")
                            captcha_image.click()
                            time.sleep(1)
                            continue
                    except Exception as e:
                        print(f"❌ 填写验证码时出错: {e}")
                        continue

                    # 点击保存按钮
                    try:
                        print("🖱️ 点击保存按钮...")
                        main_save_button = driver.find_element(By.XPATH, "//button[@type='submit' and contains(text(), '保存')]")
                        main_save_button.click()

                        # 处理确认对话框
                        confirm_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='确定']")))
                        print("🖱️ 点击确认按钮...")
                        confirm_button.click()
                    except TimeoutException:
                        print("ℹ️ 未找到保存或确认按钮")
                    except Exception as e:
                        print(f"❌ 点击保存时出错: {e}")

                    # 检查是否有验证码错误提示
                    try:
                        error_dialog = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '验证码错误')]")))
                        print(f"❌ 验证码错误，准备重试...")
                        
                        # 关闭错误对话框
                        error_confirm = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'messager-button')]//button[contains(text(),'确定')]")))
                        error_confirm.click()
                        time.sleep(1)

                        # 刷新验证码
                        captcha_image.click()
                        time.sleep(1)

                    except TimeoutException:
                        print("✅ 验证码提交成功！")
                        captcha_solved = True
                        break
                
                if not captcha_solved:
                    print("❌ 多次尝试失败，需要手动处理")
                    input("请手动完成验证码输入并提交，完成后按回车...")

            elif captcha_input:
                print("⚠️ 发现验证码但未配置API，请手动输入")
                input("请手动输入验证码并提交，完成后按回车...")
            
            else:
                print("✅ 未发现验证码")
                captcha_solved = True
                
        except Exception as e:
            print(f"ℹ️ 验证码处理时出错: {e}")
        
        if captcha_solved:
            print("\n✅ 评估表单已完成")
        else:
            print("\nℹ️ 评估可能需要手动完成")
        
        return captcha_solved
        
    except Exception as e:
        print(f"❌ 填写表单时发生致命错误: {e}")
        return False

def find_captcha_elements(driver):
    """简化的验证码元素定位"""
    print("🔍 正在定位验证码元素...")
    
    # 验证码输入框选择器（按优先级排序）
    input_selectors = [
        ("name", "adminValidateCode"),                                           # 最可能的选择器
        ("xpath", "//span[contains(text(), '验证码')]/following-sibling::input[@type='text']"),
        ("xpath", "//input[contains(@placeholder, '验证码')]"),
        ("xpath", "//input[contains(@name, 'captcha')]"),
        ("xpath", "//input[contains(@id, 'captcha')]"),
        ("xpath", "//input[contains(@id, 'validate')]")
    ]
    
    # 验证码图片选择器（按优先级排序）
    image_selectors = [
        ("id", "adminValidateImg"),                                              # 最可能的选择器
        ("xpath", "//img[contains(@id, 'captcha')]"),
        ("xpath", "//img[contains(@id, 'validate')]"),
        ("xpath", "//img[contains(@src, 'captcha')]"),
        ("xpath", "//img[contains(@src, 'validate')]")
    ]

    # 查找输入框
    captcha_input = None
    for selector_type, selector_value in input_selectors:
        try:
            if selector_type == "id":
                element = driver.find_element(By.ID, selector_value)
            elif selector_type == "name":
                element = driver.find_element(By.NAME, selector_value)
            elif selector_type == "xpath":
                element = driver.find_element(By.XPATH, selector_value)
            
            if element.is_displayed():
                captcha_input = element
                print(f"✅ 找到验证码输入框: {selector_type}='{selector_value}'")
                break
        except:
            continue
    
    # 查找图片
    captcha_image = None
    for selector_type, selector_value in image_selectors:
        try:
            if selector_type == "id":
                element = driver.find_element(By.ID, selector_value)
            elif selector_type == "xpath":
                element = driver.find_element(By.XPATH, selector_value)
            
            if element.is_displayed():
                captcha_image = element
                print(f"✅ 找到验证码图片: {selector_type}='{selector_value}'")
                break
        except:
            continue
    
    return captcha_input, captcha_image

def get_captcha_solution(driver, captcha_image, zhipu_api_key):
    """简化的验证码识别逻辑"""
    try:
        # 滚动到验证码图片，确保其完全可见
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", captcha_image)
        time.sleep(0.5)

        # 获取元素的位置和大小信息
        location = captcha_image.location
        size = captcha_image.size
        
        # 截取整个页面
        png = driver.get_screenshot_as_png()
        im = Image.open(io.BytesIO(png))
        
        # 获取设备像素比例并计算裁剪区域
        pixel_ratio = driver.execute_script("return window.devicePixelRatio") or 1
        left = int(location['x'] * pixel_ratio)
        top = int(location['y'] * pixel_ratio)
        right = int((location['x'] + size['width']) * pixel_ratio)
        bottom = int((location['y'] + size['height']) * pixel_ratio)
        
        # 确保裁剪坐标在图片范围内
        img_width, img_height = im.size
        left = max(0, min(left, img_width))
        top = max(0, min(top, img_height))
        right = max(left, min(right, img_width))
        bottom = max(top, min(bottom, img_height))
        
        # 检查裁剪区域是否合理
        if right - left <= 0 or bottom - top <= 0:
            print("⚠️ 裁剪坐标无效，使用元素截图方法")
            image_base64 = captcha_image.screenshot_as_base64
        else:
            # 执行裁剪和预处理
            im_cropped = im.crop((left, top, right, bottom))
            im_processed = im_cropped.convert('L')  # 转灰度
            enhancer = ImageEnhance.Contrast(im_processed)
            im_processed = enhancer.enhance(2)  # 增强对比度
            
            # 转换为base64
            buffer = io.BytesIO()
            im_processed.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        print("📸 验证码图片预处理完成")
        return solve_captcha_with_zhipu_llm(zhipu_api_key, image_base64)
        
    except Exception as e:
        print(f"❌ 截图或预处理验证码时发生错误: {e}")
        return None

if __name__ == "__main__":
    print("=== UCAS 快速评估工具 ===")
    print("⚠️ 本工具用于批量评估课程")
    print("⚠️ 请确保已准备好所有评估页面的URL")
    print()
    quick_evaluation() 
