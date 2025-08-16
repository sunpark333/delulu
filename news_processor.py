# news_processor.py - AI News Enhancement Module
import openai
import asyncio
import logging
from typing import Optional, Dict, Any
import config
from rate_limiter import RateLimiter
from categorizer import NewsCategori

logger = logging.getLogger(__name__)

class NewsProcessor:
    def __init__(self):
        openai.api_key = config.OPENAI_API_KEY
        self.rate_limiter = RateLimiter()
        self.categorizer = NewsCategori()
        
    async def enhance_news(self, original_news: str, user_id: int = None) -> Dict[str, Any]:
        """
        AI से news को enhance करता है
        Returns: Dict with enhanced_news, category, metrics
        """
        try:
            # Input validation
            if not self._validate_news_input(original_news):
                raise ValueError("Invalid news input")
            
            # Rate limiting check
            if user_id and not self.rate_limiter.check_rate_limit(user_id):
                raise Exception("Rate limit exceeded")
            
            # News category detect करें
            category = self.categorizer.detect_category(original_news)
            
            # AI prompt prepare करें
            enhanced_prompt = self._prepare_ai_prompt(original_news, category)
            
            # OpenAI API call
            enhanced_news = await self._call_openai_api(enhanced_prompt)
            
            # Post-processing
            final_news = self._post_process_news(enhanced_news, category)
            
            # Metrics calculate करें
            metrics = self._calculate_metrics(original_news, final_news)
            
            logger.info(f"News enhanced successfully. Length: {len(original_news)} -> {len(final_news)}")
            
            return {
                "enhanced_news": final_news,
                "category": category,
                "metrics": metrics,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error enhancing news: {e}")
            return {
                "enhanced_news": original_news,
                "category": "🔔 General",
                "metrics": {"error": str(e)},
                "success": False
            }
    
    def _validate_news_input(self, news: str) -> bool:
        """News input validation"""
        if not news or not news.strip():
            return False
        if len(news) < config.MIN_NEWS_LENGTH:
            return False
        if len(news) > config.MAX_NEWS_LENGTH:
            return False
        return True
    
    def _prepare_ai_prompt(self, original_news: str, category: str) -> str:
        """AI के लिए prompt prepare करता है"""
        category_context = {
            "🏛️ Politics": "राजनीतिक संदर्भ और background add करें",
            "💰 Business": "आर्थिक impact और market context add करें", 
            "⚽ Sports": "खेल के rules और player stats add करें",
            "🎬 Entertainment": "Celebrity background और industry context add करें",
            "🔬 Technology": "Technical details और future implications add करें",
            "🌍 International": "Global context और diplomatic angles add करें",
            "🏥 Health": "Medical context और safety guidelines add करें",
            "🎓 Education": "Educational impact और policy context add करें",
            "🌦️ Weather": "Scientific explanation और safety measures add करें",
            "🚨 Breaking": "Immediate impact और urgent context add करें"
        }
        
        category_instruction = category_context.get(category, "General context add करें")
        
        prompt = f"""
{config.AI_PROMPT_TEMPLATE}

Category: {category}
Special Focus: {category_instruction}

Original News: {original_news}

Enhanced News:
"""
        return prompt
    
    async def _call_openai_api(self, prompt: str) -> str:
        """OpenAI API call with error handling"""
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    openai.ChatCompletion.create,
                    model=config.AI_MODEL,
                    messages=[
                        {
                            "role": "system", 
                            "content": "आप एक professional news writer हैं। आपका काम news को enhance करना है।"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                ),
                timeout=config.API_TIMEOUT
            )
            
            return response.choices[0].message.content.strip()
            
        except asyncio.TimeoutError:
            logger.error("OpenAI API timeout")
            raise Exception("AI processing timeout")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception("AI processing failed")
    
    def _post_process_news(self, enhanced_news: str, category: str) -> str:
        """Post-processing enhanced news"""
        # Category emoji add करें
        if not enhanced_news.startswith(category.split()[0]):
            enhanced_news = f"{category.split()[0]} **{category.split()[1]}**\n\n{enhanced_news}"
        
        # Formatting improvements
        enhanced_news = self._improve_formatting(enhanced_news)
        
        # Add timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")
        enhanced_news += f"\n\n📅 *Updated: {timestamp}*"
        
        return enhanced_news
    
    def _improve_formatting(self, text: str) -> str:
        """Text formatting improve करता है"""
        # Basic formatting improvements
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Headings को bold बनाएं
                if len(line) < 50 and line.endswith((':','।')):
                    line = f"**{line}**"
                formatted_lines.append(line)
        
        return '\n\n'.join(formatted_lines)
    
    def _calculate_metrics(self, original: str, enhanced: str) -> Dict[str, Any]:
        """News enhancement metrics calculate करता है"""
        return {
            "original_length": len(original),
            "enhanced_length": len(enhanced),
            "improvement_ratio": len(enhanced) / len(original) if len(original) > 0 else 0,
            "words_added": len(enhanced.split()) - len(original.split()),
            "processing_time": "< 5 seconds"
        }
    
    async def bulk_enhance_news(self, news_list: list, user_id: int = None) -> list:
        """Multiple news items को एक साथ enhance करता है"""
        results = []
        for news in news_list:
            result = await self.enhance_news(news, user_id)
            results.append(result)
            # Rate limiting के लिए delay
            await asyncio.sleep(1)
        return results