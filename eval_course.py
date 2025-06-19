#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UCAS 课程评估工具 - 支持多选题版本
功能：自动化填写包含多选题的课程评估表单
作者：AI Assistant
"""

import time
import base64
import io
import re
import requests
import jwt
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from PIL import Image, ImageEnhance

def debug_page_structure(driver):
    """调试页面结构，帮助理解表单组织方式"""
    print("\n🔍 === 页面结构分析 ===")
    
    try:
        # 查找所有表格行
        rows = driver.find_elements(By.XPATH, "//tr")
        print(f"📊 发现 {len(rows)} 个表格行")
        
        for i, row in enumerate(rows[:10]):  # 只显示前10行
            try:
                text = row.text.strip()
                if text:
                    print(f"   第{i+1}行: {text[:100]}...")
            except:
                pass
        
        # 查找所有单选按钮
        radio_buttons = driver.find_elements(By.XPATH, "//input[@type='radio']")
        print(f"📻 发现 {len(radio_buttons)} 个单选按钮")
        
        # 查找所有复选框
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        print(f"☑️ 发现 {len(checkboxes)} 个复选框")
        
        # 查找所有文本域
        textareas = driver.find_elements(By.XPATH, "//textarea")
        print(f"📝 发现 {len(textareas)} 个文本域")
        
        # 查找验证码相关元素
        captcha_inputs = driver.find_elements(By.XPATH, "//input[contains(@name, 'validate') or contains(@name, 'captcha')]")
        captcha_images = driver.find_elements(By.XPATH, "//img[contains(@id, 'validate') or contains(@id, 'captcha')]")
        print(f"🤖 发现 {len(captcha_inputs)} 个验证码输入框，{len(captcha_images)} 个验证码图片")
        
    except Exception as e:
        print(f"❌ 分析页面结构时出错: {e}")

def quick_evaluation():
    """快速评估主函数 - 循环处理模式"""
    print("=== UCAS 课程评估工具（多选题版本）===")
    print("📝 本工具支持包含多选题的评估表单")
    print("🔄 循环模式：每次处理一个评估页面")
    print()
    
    # 设置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 启动浏览器
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # 优化启动流程：先导航到登录页
        login_url = "https://sep.ucas.ac.cn/"
        print(f"🌐 正在打开登录页面: {login_url}")
        driver.get(login_url)
        
        input("请在浏览器中完成登录，然后回到这里按回车键继续...")
        print("✅ 登录完成，准备开始评估。")
        
        # 获取智谱AI API密钥（可选）
        zhipu_api_key = input("请输入智谱AI API密钥（直接回车跳过，将手动处理验证码）: ").strip()
        if not zhipu_api_key:
            zhipu_api_key = None
            print("⚠️ 未配置API密钥，验证码需要手动处理")
        else:
            print("✅ 已配置智谱AI API，将自动识别验证码")
        
        evaluation_count = 0
        
        while True:
            evaluation_count += 1
            print(f"\n🎯 === 第 {evaluation_count} 次评估 ===")
            
            # 获取评估页面URL
            url = input("请输入评估页面URL（输入 'quit' 退出）: ").strip()
            
            if url.lower() == 'quit':
                print("👋 退出程序")
                break
            
            if not url:
                print("❌ URL不能为空")
                continue
            
            try:
                print(f"🌐 正在访问: {url}")
                driver.get(url)
                time.sleep(2)
                
                # 调试页面结构（可选）
                debug_choice = input("是否分析页面结构？(y/n，默认n): ").strip().lower()
                if debug_choice == 'y':
                    debug_page_structure(driver)
                
                # 填写评估表单
                success = fill_evaluation_form_with_multiselect(driver, zhipu_api_key)
                
                if success:
                    print(f"✅ 第 {evaluation_count} 次评估完成")
                else:
                    print(f"⚠️ 第 {evaluation_count} 次评估可能需要手动确认")
                
                # 询问是否继续
                continue_choice = input("\n继续下一个评估？(y/n，默认y): ").strip().lower()
                if continue_choice == 'n':
                    print("👋 评估结束")
                    break
                    
            except Exception as e:
                print(f"❌ 处理第 {evaluation_count} 次评估时出错: {e}")
                continue
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
    finally:
        input("按回车关闭浏览器...")
        driver.quit()
        print("🎉 浏览器已关闭，程序结束")

def generate_zhipu_token(apikey: str):
    """生成智谱AI的JWT token"""
    try:
        api_key_part, secret = apikey.split(".", 1)
    except Exception:
        raise Exception("invalid apikey", apikey)

    payload = {
        "api_key": api_key_part,
        "exp": int((datetime.now() + timedelta(days=1)).timestamp() * 1000),
        "timestamp": int(datetime.now().timestamp() * 1000),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )

def solve_captcha_with_zhipu_llm(api_key, image_base64):
    """使用智谱AI GLM-4V模型识别验证码"""
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
    """点击单选按钮，支持多种点击方式"""
    try:
        if radio_element.is_enabled() and radio_element.is_displayed():
            driver.execute_script("arguments[0].click();", radio_element)
            time.sleep(0.1)
            return True
    except Exception as e:
        print(f"⚠️ 第{row_num}行单选按钮点击失败: {e}")
        return False
    return False

def click_checkbox(driver, checkbox_element, option_text):
    """点击复选框，支持多种点击方式"""
    try:
        if checkbox_element.is_enabled() and checkbox_element.is_displayed():
            driver.execute_script("arguments[0].click();", checkbox_element)
            time.sleep(0.1)
            return True
    except Exception as e:
        print(f"⚠️ 复选框'{option_text}'点击失败: {e}")
        return False
    return False

def fill_evaluation_form_with_multiselect(driver, zhipu_api_key=None):
    """填写包含多选题的评估表单"""
    try:
        print("🚀 开始填写评估表单...")
        
        # 等待页面加载
        time.sleep(2)
        
        # === 第一部分：处理单选按钮（评估评分） ===
        print("\n📻 === 处理单选按钮评估 ===")
        
        # 策略1：按表格行处理单选按钮
        radio_success = fill_radio_buttons_by_table_rows(driver)
        
        if not radio_success:
            # 策略2：按name属性分组处理
            print("🔄 尝试按name属性分组处理单选按钮...")
            radio_success = fill_radio_buttons_by_name_groups(driver)
        
        if not radio_success:
            # 策略3：顺序选择策略
            print("🔄 尝试顺序选择策略...")
            radio_success = fill_radio_buttons_sequential(driver)
        
        if radio_success:
            print("✅ 单选按钮填写完成")
        else:
            print("⚠️ 单选按钮填写可能不完整")
        
        # === 第二部分：处理复选框（多选题） ===
        print("\n☑️ === 处理多选题 ===")
        multiselect_success = fill_multiselect_questions(driver)
        
        # === 第三部分：处理文本域 ===
        print("\n📝 === 填写文本域 ===")
        textarea_success = fill_text_areas(driver)
        
        # === 第四部分：处理验证码和提交 ===
        print("\n🤖 === 处理验证码和提交 ===")
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
                        
                        # 使用更通用的选择器列表来查找保存按钮
                        submit_selectors = [
                            "//button[@type='submit' and contains(text(), '保存')]",
                            "//input[@type='submit' and contains(@value, '保存')]",
                            "//button[contains(text(), '保存')]",
                            "//a[contains(text(), '保存')]"
                        ]
                        
                        main_save_button = None
                        for selector in submit_selectors:
                            try:
                                button = driver.find_element(By.XPATH, selector)
                                if button.is_displayed() and button.is_enabled():
                                    main_save_button = button
                                    print(f"   ✅ 使用选择器找到按钮: {selector}")
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if main_save_button:
                            main_save_button.click()
                        else:
                            raise NoSuchElementException("所有预设的选择器都无法找到'保存'按钮")

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

def fill_radio_buttons_by_table_rows(driver):
    """策略1：按表格行处理单选按钮"""
    try:
        print("🎯 策略1: 按表格行处理单选按钮...")
        
        # 查找包含单选按钮的表格行
        radio_rows = driver.find_elements(By.XPATH, "//tr[.//input[@type='radio']]")
        
        if not radio_rows:
            print("⚠️ 未找到包含单选按钮的表格行")
            return False
        
        print(f"📊 发现 {len(radio_rows)} 行包含单选按钮")
        
        success_count = 0
        for i, row in enumerate(radio_rows, 1):
            try:
                # 在每行中查找单选按钮
                radios_in_row = row.find_elements(By.XPATH, ".//input[@type='radio']")
                
                if radios_in_row:
                    # 选择第一个单选按钮（最高评价）
                    first_radio = radios_in_row[0]
                    
                    if click_radio_button(driver, first_radio, i):
                        success_count += 1
                        print(f"✅ 第{i}行: 已选择最高评价选项")
                    else:
                        print(f"❌ 第{i}行: 单选按钮点击失败")
                        
            except Exception as e:
                print(f"❌ 处理第{i}行时出错: {e}")
        
        print(f"📈 单选按钮处理结果: {success_count}/{len(radio_rows)} 行成功")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 表格行策略执行失败: {e}")
        return False

def fill_radio_buttons_by_name_groups(driver):
    """策略2：按name属性分组处理单选按钮"""
    try:
        print("🎯 策略2: 按name属性分组...")
        
        all_radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        if not all_radios:
            return False
        
        # 按name属性分组
        name_groups = {}
        for radio in all_radios:
            name = radio.get_attribute("name")
            if name and "captcha" not in name.lower() and "validate" not in name.lower():
                if name not in name_groups:
                    name_groups[name] = []
                name_groups[name].append(radio)
        
        print(f"📊 发现 {len(name_groups)} 个单选按钮组")
        
        success_count = 0
        for name, radios in name_groups.items():
            try:
                # 选择第一个选项（通常是最高评价）
                first_radio = radios[0]
                if click_radio_button(driver, first_radio, name):
                    success_count += 1
                    print(f"✅ 组'{name}': 已选择最高评价选项")
                    
            except Exception as e:
                print(f"❌ 处理组'{name}'时出错: {e}")
        
        print(f"📈 name分组处理结果: {success_count}/{len(name_groups)} 组成功")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ name分组策略执行失败: {e}")
        return False

def fill_radio_buttons_sequential(driver):
    """策略3：顺序选择策略"""
    try:
        print("🎯 策略3: 顺序选择...")
        
        all_radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        if not all_radios:
            return False
        
        # 过滤掉验证码相关的单选按钮
        eval_radios = []
        for radio in all_radios:
            name = radio.get_attribute("name") or ""
            if "captcha" not in name.lower() and "validate" not in name.lower():
                eval_radios.append(radio)
        
        print(f"📊 发现 {len(eval_radios)} 个评估单选按钮")
        
        # 智能选择：每5个为一组，选择第1个（最高评价）
        success_count = 0
        for i in range(0, len(eval_radios), 5):
            try:
                radio = eval_radios[i]
                if click_radio_button(driver, radio, i//5 + 1):
                    success_count += 1
                    print(f"✅ 第{i//5 + 1}题: 已选择最高评价")
                    
            except Exception as e:
                print(f"❌ 处理第{i//5 + 1}题时出错: {e}")
        
        print(f"📈 顺序选择结果: {success_count} 题成功")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 顺序选择策略执行失败: {e}")
        return False

def fill_multiselect_questions(driver):
    """处理多选题（复选框）"""
    try:
        print("🎯 开始处理多选题...")
        
        # 查找所有复选框
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox']")
        
        if not checkboxes:
            print("ℹ️ 未发现复选框，跳过多选题处理")
            return True
        
        print(f"☑️ 发现 {len(checkboxes)} 个复选框")
        
        # 根据页面内容，智能选择合适的选项
        # 对于"修读原因"类型的多选题，选择前2-3个比较合理的选项
        
        success_count = 0
        selected_count = 0
        max_selections = 3  # 最多选择3个选项
        
        for i, checkbox in enumerate(checkboxes):
            try:
                # 如果已经选择了足够的选项，跳过剩余的
                if selected_count >= max_selections:
                    break
                
                # 获取复选框的相关文本（用于调试）
                try:
                    parent = checkbox.find_element(By.XPATH, "./..")
                    option_text = parent.text.strip()[:50]  # 截取前50个字符
                except:
                    option_text = f"选项{i+1}"
                
                # 选择前几个选项
                if checkbox.is_enabled() and checkbox.is_displayed():
                    driver.execute_script("arguments[0].click();", checkbox)
                    time.sleep(0.1)
                    success_count += 1
                    selected_count += 1
                    print(f"✅ 已选择: {option_text}")
                    
            except Exception as e:
                print(f"❌ 处理复选框{i+1}时出错: {e}")
        
        print(f"📈 多选题处理结果: 成功选择 {selected_count} 个选项")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 多选题处理失败: {e}")
        return False

def fill_text_areas(driver):
    """填写文本域"""
    try:
        textareas = driver.find_elements(By.XPATH, "//textarea")
        
        if not textareas:
            print("ℹ️ 未发现文本域")
            return True
        
        print(f"📝 发现 {len(textareas)} 个文本域")
        
        # 通用的正面评价文本
        positive_comments = [
            "课程内容丰富，教学方法得当，受益匪浅。",
            "老师讲解清晰，课程安排合理，学习效果良好。",
            "教学质量高，内容实用，对专业学习很有帮助。",
            "课程设计合理，教师专业水平高，值得推荐。"
        ]
        
        success_count = 0
        for i, textarea in enumerate(textareas):
            try:
                # 选择一个评价文本
                comment = positive_comments[i % len(positive_comments)]
                
                # 填写文本
                driver.execute_script("arguments[0].value = arguments[1];", textarea, comment)
                time.sleep(0.2)
                
                success_count += 1
                print(f"✅ 文本域{i+1}: 已填写评价内容")
                
            except Exception as e:
                print(f"❌ 填写文本域{i+1}时出错: {e}")
        
        print(f"📈 文本域填写结果: {success_count}/{len(textareas)} 个成功")
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 文本域填写失败: {e}")
        return False

def find_captcha_elements(driver):
    """简化的验证码元素定位"""
    print("🔍 正在定位验证码元素...")
    
    # 验证码输入框选择器（按优先级排序）
    input_selectors = [
        ("name", "adminValidateCode"),
        ("xpath", "//span[contains(text(), '验证码')]/following-sibling::input[@type='text']"),
        ("xpath", "//input[contains(@placeholder, '验证码')]"),
        ("xpath", "//input[contains(@name, 'captcha')]"),
        ("xpath", "//input[contains(@id, 'captcha')]"),
        ("xpath", "//input[contains(@id, 'validate')]")
    ]
    
    # 验证码图片选择器（按优先级排序）
    image_selectors = [
        ("id", "adminValidateImg"),
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
    print("=== UCAS 课程评估工具（多选题版本）===")
    print("⚠️ 本工具支持包含多选题的评估表单")
    print("⚠️ 请确保已准备好所有评估页面的URL")
    print()
    quick_evaluation() 
